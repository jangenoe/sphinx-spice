import re
import docutils

from sphinx.transforms import SphinxTransform
from sphinx.util import logging
from sphinx.errors import ExtensionError

# from sphinx.errors import ExtensionError

from ._compat import findall
from .nodes import (
    spice_file_node,
    spice_file_enumerable_node,
    spice_file_end_node,
    spice_simulation_node,
    spice_simulation_start_node,
    spice_simulation_end_node,
)

logger = logging.getLogger(__name__)


class CheckGatedDirectives(SphinxTransform):
    """
    This transform checks the structure of the gated spice_simulations
    to flag any errors in input
    """

    default_priority = 1

    def check_structure(self, registry):
        """Check Structure of the Gated Registry"""
        error = False
        docname = self.env.docname
        if docname in registry:
            start = registry[docname]["start"]
            end = registry[docname]["end"]
            sequence = "".join(registry[docname]["sequence"])
            structure = "\n  ".join(registry[docname]["msg"])
            nodetype = registry[docname]["type"]
            if len(start) > len(end):
                msg = f"The document ({docname}) is missing a {nodetype}-end directive\n  {structure}"  # noqa: E501
                logger.error(msg)
                error = True
            if len(start) < len(end):
                msg = f"The document ({docname}) is missing a {nodetype}-start directive\n  {structure}"  # noqa: E501
                logger.error(msg)
                error = True
            if len(start) == len(end):
                groups = re.findall("(SE)", sequence)
                if len(groups) != len(start):
                    msg = f"The document ({docname}) contains nested {nodetype}-start and {nodetype}-end directives\n  {structure}"  # noqa: E501
                    logger.error(msg)
                    error = True
        if error:
            msg = "[sphinx-spice_file] An error has occured when parsing gated directives.\nPlease check warning messages above"  # noqa: E501
            raise ExtensionError(message=msg)

    def apply(self):
        # Check structure of all -start and -end nodes
        if hasattr(self.env, "sphinx_spice_file_gated_registry"):
            self.check_structure(self.env.sphinx_spice_file_gated_registry)


class MergeGatedspice_simulations(SphinxTransform):
    """
    Transform Gated Directives into single unified
    Directives in the Sphinx Abstract Syntax Tree

    Note: The CheckGatedspice_simulations Transform should ensure the
    structure of the gated directives is correct before
    this transform is run.
    """

    default_priority = 10

    def find_nodes(self, label, node):
        parent_node = node.parent
        parent_start, parent_end = None, None
        for idx1, child in enumerate(parent_node.children):
            if isinstance(child, spice_simulation_start_node) and label == child.get("label"):
                parent_start = idx1
                for idx2, child2 in enumerate(parent_node.children[parent_start:]):
                    if isinstance(child2, spice_simulation_end_node):
                        parent_end = idx1 + idx2
                        break
                break
        return parent_start, parent_end

    def apply(self):
        # Process all matching spice_simulation-start and spice_simulation-end nodes
        for node in findall(self.document, spice_simulation_start_node):
            label = node.get("label")
            parent_start, parent_end = self.find_nodes(label, node)
            if not parent_end:
                continue
            parent = node.parent
            # Rebuild Node as a spice_simulation Node
            new_node = spice_simulation_node()
            new_node.attributes = node.attributes
            # Update Attributes
            new_node["classes"] = [
                attr.replace("spice_simulation-start", "spice_simulation")
                for attr in node.attributes["classes"]
            ]
            new_node["type"] = "spice_simulation"
            new_node.parent = node.parent
            for child in node.children:
                if type(child) is docutils.nodes.section:
                    pass
                else:
                    new_node += child
            # Collect nodes attached to the Parent Node until :spice_simulation-end:
            content = docutils.nodes.section(
                ids=["spice_simulation-content"]
            )  # TODO: should id be classes?
            for child in parent.children[parent_start + 1 : parent_end]:
                content += child
            new_node += content
            # Replace :spice_simulation-start: with new spice_simulation node
            node.replace_self(new_node)
            # Clean up Parent Node including :spice_simulation-end:
            for child in parent.children[parent_start + 1 : parent_end + 1]:
                parent.remove(child)


class MergeGatedspice_files(SphinxTransform):
    """
    Transform Gated spice_file Directives into single unified
    Directives in the Sphinx Abstract Syntax Tree

    Note: The CheckGatedDirectives Transform should ensure the
    structure of the gated directives is correct before
    this transform is run.
    """

    default_priority = 10

    def find_nodes(self, label, node):
        parent_node = node.parent
        parent_start, parent_end = None, None
        for idx1, child in enumerate(parent_node.children):
            if isinstance(
                child, (spice_file_node, spice_file_enumerable_node)
            ) and label == child.get("label"):
                parent_start = idx1
                for idx2, child2 in enumerate(parent_node.children[parent_start:]):
                    if isinstance(child2, spice_file_end_node):
                        parent_end = idx1 + idx2
                        break
                break
        return parent_start, parent_end

    def merge_nodes(self, node):
        label = node.get("label")
        parent_start, parent_end = self.find_nodes(label, node)
        if not parent_end:
            return
        parent = node.parent
        # Use Current Node and remove "-start" from class names and type
        updated_classes = [
            cls.replace("-start", "") for cls in node.attributes["classes"]
        ]
        node.attributes["classes"] = updated_classes
        node.attributes["type"] = node.attributes["type"].replace("-start", "")
        # Attach content to section
        content = node.children[-1]
        for child in parent.children[parent_start + 1 : parent_end]:
            content += child
        # Clean up Parent Node including :spice_file-end:
        for child in parent.children[parent_start + 1 : parent_end + 1]:
            parent.remove(child)

    def apply(self):
        # Process all matching spice_file and spice_file-enumerable (gated=True)
        # and spice_file-end nodes
        for node in findall(self.document, spice_file_node):
            if node.gated:
                self.merge_nodes(node)
            node.gated = False
        for node in findall(self.document, spice_file_enumerable_node):
            if node.gated:
                self.merge_nodes(node)
            node.gated = False
