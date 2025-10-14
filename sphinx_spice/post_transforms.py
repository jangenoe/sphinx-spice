import sphinx.addnodes as sphinx_nodes
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import logging
from sphinx.builders.latex import LaTeXBuilder
from docutils import nodes as docutil_nodes

from ._compat import findall
from .utils import get_node_number, find_parent
from .nodes import (
    spice_file_enumerable_node,
    spice_simulation_node,
    spice_file_title,
    spice_file_subtitle,
    spice_simulation_title,
    is_spice_file_node,
    spice_file_latex_number_reference,
)

logger = logging.getLogger(__name__)


def build_reference_node(app, target_node):
    """
    Builds a docutil.nodes.reference object
    to a given target_node.
    """
    refuri = app.builder.get_relative_uri(
        app.env.docname, target_node.get("docname", "")
    )
    refuri += "#" + target_node.get("label")
    reference = docutil_nodes.reference(
        "",
        "",
        internal=True,
        refuri=refuri,
        anchorname="",
    )
    return reference


class UpdateReferencesToEnumerated(SphinxPostTransform):
    """
        Updates all :ref: to :numref: if used when referencing
        an enumerated spice_file node.
    ]"""

    default_priority = 5

    def run(self):
        if not hasattr(self.env, "sphinx_spice_file_registry"):
            return

        for node in findall(self.document, sphinx_nodes.pending_xref):
            if node.get("reftype") != "numref":
                target_label = node.get("reftarget")
                if target_label in self.env.sphinx_spice_file_registry:
                    target = self.env.sphinx_spice_file_registry[target_label]
                    target_node = target.get("node")
                    if isinstance(target_node, spice_file_enumerable_node):
                        # Don't Modify Custom Text
                        if node.get("refexplicit"):
                            continue
                        node["reftype"] = "numref"
                        # Get Metadata from Inline
                        inline = node.children[0]
                        classes = inline["classes"]
                        classes.remove("std-ref")
                        classes.append("std-numref")
                        # Construct a Literal Node
                        literal = docutil_nodes.literal()
                        literal["classes"] = classes
                        literal.children += inline.children
                        node.children[0] = literal


class ResolveTitlesInspice_files(SphinxPostTransform):
    """
    Resolve Titles for spice_file Nodes and Enumerated spice_file Nodes
    for:
        1. Numbering
        2. Formatting Title and Subtitles into docutils.title node
    """

    default_priority = 20

    def resolve_title(self, node):
        title = node.children[0]
        if isinstance(title, spice_file_title):
            updated_title = docutil_nodes.title()
            if isinstance(node, spice_file_enumerable_node):
                # Numfig (HTML) will use "spice_file %s" so we just need the subtitle
                if self.app.builder.format == "latex":
                    # Resolve Title
                    node_number = get_node_number(self.app, node, "spice_file")
                    title_text = self.app.config.numfig_format["spice_file"] % node_number
                    updated_title += docutil_nodes.Text(title_text)
                updated_title["title"] = self.app.config.numfig_format["spice_file"]
            else:
                # Use default text "spice_file"
                updated_title += title.children[0]
            # Parse Custom Titles
            if len(title.children) > 1:
                subtitle = title.children[1]
                if isinstance(subtitle, spice_file_subtitle):
                    updated_title += docutil_nodes.Text(" (")
                    for child in subtitle.children:
                        updated_title += child
                    updated_title += docutil_nodes.Text(")")
            updated_title.parent = title.parent
            node.children[0] = updated_title
        node.resolved_title = True
        return node

    def run(self):
        if not hasattr(self.env, "sphinx_spice_file_registry"):
            return

        for node in findall(self.document, is_spice_file_node):
            node = self.resolve_title(node)


# spice_simulation Nodes


def resolve_spice_simulation_title(app, node, spice_file_node):
    """
    Resolve Titles for spice_simulation Nodes for:

        1. Numbering of Target spice_file Nodes
        2. Formatting Title and Subtitles into docutils.title node
        3. Ensure mathjax is triggered for pages that include path
           in titles inherited from spice_file Node

    Note: Setup as a resolver function in case we need to resolve titles
    in references to spice_simulation nodes.
    """

    title = node.children[0]
    spice_file_title = spice_file_node.children[0]
    if isinstance(title, spice_simulation_title):
        entry_title_text = node.get("title")
        updated_title_text = " " + spice_file_title.children[0].astext()
        if isinstance(spice_file_node, spice_file_enumerable_node):
            node_number = get_node_number(app, spice_file_node, "spice_file")
            updated_title_text += f" {node_number}"
        # New Title Node
        updated_title = docutil_nodes.title()
        wrap_reference = build_reference_node(app, spice_file_node)
        wrap_reference += docutil_nodes.Text(updated_title_text)
        node["title"] = entry_title_text + updated_title_text
        # Parse Custom Titles from spice_file
        if len(spice_file_title.children) > 1:
            subtitle = spice_file_title.children[1]
            if isinstance(subtitle, spice_file_subtitle):
                wrap_reference += docutil_nodes.Text(" (")
                for child in subtitle.children:
                    if isinstance(child, docutil_nodes.math):
                        # Ensure mathjax is loaded for pages that only contain
                        # references to nodes that contain math
                        domain = app.env.get_domain("math")
                        domain.data["has_equations"][app.env.docname] = True
                    wrap_reference += child
                wrap_reference += docutil_nodes.Text(")")
        updated_title += docutil_nodes.Text(entry_title_text)
        updated_title += wrap_reference
        updated_title.parent = title.parent
        node.children[0] = updated_title
    node.resolved_title = True
    return node


class ResolveTitlesInspice_simulations(SphinxPostTransform):
    default_priority = 21

    def run(self):
        if not hasattr(self.env, "sphinx_spice_file_registry"):
            return

        # Update spice_simulation Directives
        for node in findall(self.document, spice_simulation_node):
            label = node.get("label")
            target_label = node.get("target_label")
            try:
                target = self.env.sphinx_spice_file_registry[target_label]
                target_node = target.get("node")
                node = resolve_spice_simulation_title(self.app, node, target_node)
                # Update Registry
                self.env.sphinx_spice_file_registry[label]["node"] = node
            except Exception:
                if isinstance(self.app.builder, LaTeXBuilder):
                    docname = find_parent(self.app.builder.env, node, "section")
                else:
                    try:
                        docname = self.app.builder.current_docname
                    except AttributeError:
                        docname = self.env.docname  # for builder such as JupyterBuilder that don't support current_docname
                docpath = self.env.doc2path(docname)
                path = docpath[: docpath.rfind(".")]
                msg = f"undefined label: {target_label}"
                logger.warning(msg, location=path, color="red")
                return


class ResolveLinkTextTospice_simulations(SphinxPostTransform):
    """
    Resolve Titles for spice_simulations Nodes and merge in
    the main title only from target_nodes
    """

    default_priority = 22

    def run(self):
        if not hasattr(self.env, "sphinx_spice_file_registry"):
            return

        # Update spice_simulation References
        for node in findall(self.document, docutil_nodes.reference):
            refid = node.get("refid")
            if refid in self.env.sphinx_spice_file_registry:
                target = self.env.sphinx_spice_file_registry[refid]
                target_node = target.get("node")
                if self.app.builder.format == "latex":
                    if isinstance(target_node, spice_file_enumerable_node):
                        new_node = spice_file_latex_number_reference()
                        new_node.parent = node.parent
                        new_node.attributes = node.attributes
                        for child in node.children:
                            new_node += child
                        node.replace_self(new_node)
                if isinstance(target_node, spice_simulation_node):
                    # TODO: Check if this condition is required?
                    if not target_node.resolved_title:
                        spice_file_label = target_node.get("target_label")
                        spice_file_target = self.env.sphinx_spice_file_registry[
                            spice_file_label
                        ]  # noqa: E501
                        spice_file_node = spice_file_target.get("node")
                        target_node = resolve_spice_simulation_title(
                            self.app, target_node, spice_file_node
                        )  # noqa: E501
                    title_text = target_node.children[0].astext()
                    inline = node.children[0]
                    inline.children = []
                    inline += docutil_nodes.Text(title_text)
                    node.children[0] = inline
