"""
sphinx_spice_file.directive
~~~~~~~~~~~~~~~~~~~~~~~~~

A custom Sphinx Directive

:copyright: Copyright 2020 by the QuantEcon team, see AUTHORS
:licences: see LICENSE for details
"""

from typing import List
from docutils.nodes import Node

from sphinx.util.docutils import SphinxDirective
from docutils.parsers.rst import directives
from .nodes import (
    spice_file_node,
    spice_file_enumerable_node,
    spice_file_end_node,
    spice_simulation_node,
    spice_simulation_start_node,
    spice_simulation_end_node,
    spice_file_title,
    spice_file_subtitle,
    spice_simulation_title,
)
from docutils import nodes
from sphinx.util import logging

logger = logging.getLogger(__name__)


class Sphinxspice_fileBaseDirective(SphinxDirective):
    def duplicate_labels(self, label):
        """Check for duplicate labels"""

        if not label == "" and label in self.env.sphinx_spice_file_registry.keys():
            docpath = self.env.doc2path(self.env.docname)
            path = docpath[: docpath.rfind(".")]
            other_path = self.env.doc2path(
                self.env.sphinx_spice_file_registry[label]["docname"]
            )
            msg = f"duplicate label: {label}; other instance in {other_path}"
            logger.warning(msg, location=path, color="red")
            return True

        return False


class spice_fileDirective(Sphinxspice_fileBaseDirective):
    """
    An spice_file directive

    .. spice_file:: <subtitle> (optional)
       :label:
       :class:
       :nonumber:
       :hidden:

    Arguments
    ---------
    subtitle : str (optional)
            Specify a custom subtitle to add to the spice_file output

    Parameters:
    -----------
    label : str,
            A unique identifier for your spice_file that you can use to reference
            it with {ref} and {numref}
    class : str,
            Value of the spice_file’s class attribute which can be used to add custom CSS
    nonumber :  boolean (flag),
                Turns off spice_file auto numbering.
    hidden  :   boolean (flag),
                Removes the directive from the final output.
    """

    name = "spice_file"
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        "label": directives.unchanged_required,
        "class": directives.class_option,
        "nonumber": directives.flag,
        "hidden": directives.flag,
    }

    def run(self) -> List[Node]:
        self.defaults = {"title_text": "spice_file"}
        self.serial_number = self.env.new_serialno()

        # Initialise Registry (if needed)
        if not hasattr(self.env, "sphinx_spice_file_registry"):
            self.env.sphinx_spice_file_registry = {}

        # Construct Title
        title = spice_file_title()
        title += nodes.Text(self.defaults["title_text"])

        # Select Node Type and Initialise
        if "nonumber" in self.options:
            node = spice_file_node()
        else:
            node = spice_file_enumerable_node()

        if self.name == "spice_file-start":
            node.gated = True

        # Parse custom subtitle option
        if self.arguments != []:
            subtitle = spice_file_subtitle()
            subtitle_text = f"{self.arguments[0]}"
            subtitle_nodes, _ = self.state.inline_text(subtitle_text, self.lineno)
            for subtitle_node in subtitle_nodes:
                subtitle += subtitle_node
            title += subtitle

        # State Parsing
        section = nodes.section(ids=["spice_file-content"])
        self.state.nested_parse(self.content, self.content_offset, section)

        # Construct a label
        label = self.options.get("label", "")
        if label:
            # TODO: Check how :noindex: is used here
            self.options["noindex"] = False
        else:
            self.options["noindex"] = True
            label = f"{self.env.docname}-spice_file-{self.serial_number}"

        # Check for Duplicate Labels
        # TODO: Should we just issue a warning rather than skip content?
        if self.duplicate_labels(label):
            return []

        # Collect Classes
        classes = [f"{self.name}"]
        if self.options.get("class"):
            classes.extend(self.options.get("class"))

        self.options["name"] = label

        # Construct Node
        node += title
        node += section
        node["classes"].extend(classes)
        node["ids"].append(label)
        node["label"] = label
        node["docname"] = self.env.docname
        node["title"] = self.defaults["title_text"]
        node["type"] = self.name
        node["hidden"] = True if "hidden" in self.options else False
        node["serial_number"] = self.serial_number
        node.document = self.state.document

        self.add_name(node)
        self.env.sphinx_spice_file_registry[label] = {
            "type": self.name,
            "docname": self.env.docname,
            # Copy the node so that the post transforms do not modify this original state
            # Prior to Sphinx 6.1.0, the doctree was not cached, and Sphinx loaded a new copy
            # c.f. https://github.com/sphinx-doc/sphinx/commit/463a69664c2b7f51562eb9d15597987e6e6784cd
            "node": node.deepcopy(),
        }

        # TODO: Could tag this as Hidden to prevent the cell showing
        # rather than removing content
        # https://github.com/executablebooks/sphinx-jupyterbook-latex/blob/8401a27417d8c2dadf0365635bd79d89fdb86550/sphinx_jupyterbook_latex/transforms.py#L108
        if node.get("hidden", bool):
            return []

        return [node]


class spice_simulationDirective(Sphinxspice_fileBaseDirective):
    """
    A spice_simulation directive

    .. spice_simulation:: <spice_file-reference>
       :label:
       :class:
       :hidden:

    Arguments
    ---------
    spice_file-reference : str
                        Specify a linked spice_file by label

    Parameters:
    -----------
    label : str,
            A unique identifier for your spice_file that you can use to reference
            it with {ref} and {numref}
    class : str,
            Value of the spice_file’s class attribute which can be used to add custom CSS
    hidden  :   boolean (flag),
                Removes the directive from the final output.

    Notes:
    ------
    Checking for target reference is done in post_transforms for spice_simulation Titles
    """

    name = "spice_simulation"
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "label": directives.unchanged_required,
        "class": directives.class_option,
        "hidden": directives.flag,
    }
    spice_simulation_node = spice_simulation_node

    def run(self) -> List[Node]:
        self.defaults = {"title_text": "spice_simulation to"}
        target_label = self.arguments[0]
        self.serial_number = self.env.new_serialno()

        # Initialise Registry if Required
        if not hasattr(self.env, "sphinx_spice_file_registry"):
            self.env.sphinx_spice_file_registry = {}

        # Parse :hide-spice_simulations: option
        if self.env.app.config.hide_spice_simulations:
            return []

        # Construct Title
        title = spice_simulation_title()
        title += nodes.Text(self.defaults["title_text"])

        # State Parsing
        section = nodes.section(ids=["spice_simulation-content"])
        self.state.nested_parse(self.content, self.content_offset, section)

        # Fetch Label or Generate One
        label = self.options.get("label", "")
        if label:
            # TODO: Check how :noindex: is used here
            self.options["noindex"] = False
        else:
            self.options["noindex"] = True
            label = f"{self.env.docname}-spice_simulation-{self.serial_number}"

        # Check for duplicate labels
        # TODO: Should we just issue a warning rather than skip content?
        if self.duplicate_labels(label):
            return []

        self.options["name"] = label

        # Collect Classes
        classes = [f"{self.name}"]
        if self.options.get("class"):
            classes += self.options.get("class")

        # Construct Node
        node = self.spice_simulation_node()
        node += title
        node += section
        node["target_label"] = target_label
        node["classes"].extend(classes)
        node["ids"].append(label)
        node["label"] = label
        node["docname"] = self.env.docname
        node["title"] = title.astext()
        node["type"] = self.name
        node["hidden"] = True if "hidden" in self.options else False
        node["serial_number"] = self.serial_number
        node.document = self.state.document

        self.add_name(node)
        self.env.sphinx_spice_file_registry[label] = {
            "type": self.name,
            "docname": self.env.docname,
            "node": node,
        }

        if node.get("hidden", bool):
            return []

        return [node]


# Gated Directives


class spice_fileStartDirective(spice_fileDirective):
    """
    A gated directive for spice_files

    .. spice_file:: <subtitle> (optional)
       :label:
       :class:
       :nonumber:
       :hidden:

    This class is a child of spice_fileDirective so it supports
    all the same options as the base spice_file node
    """

    name = "spice_file-start"

    def run(self):
        # Initialise Gated Registry
        if not hasattr(self.env, "sphinx_spice_file_gated_registry"):
            self.env.sphinx_spice_file_gated_registry = {}
        gated_registry = self.env.sphinx_spice_file_gated_registry
        docname = self.env.docname
        if docname not in gated_registry:
            gated_registry[docname] = {
                "start": [],
                "end": [],
                "sequence": [],
                "msg": [],
                "type": "spice_file",
            }
        gated_registry[self.env.docname]["start"].append(self.lineno)
        gated_registry[self.env.docname]["sequence"].append("S")
        gated_registry[self.env.docname]["msg"].append(
            f"{self.name} at line: {self.lineno}"
        )
        # Run Parent Methods
        return super().run()


class spice_fileEndDirective(SphinxDirective):
    """
    A simple gated directive to mark end of an spice_file

    .. spice_file-end::
    """

    name = "spice_file-end"

    def run(self):
        # Initialise Gated Registry
        if not hasattr(self.env, "sphinx_spice_file_gated_registry"):
            self.env.sphinx_spice_file_gated_registry = {}
        gated_registry = self.env.sphinx_spice_file_gated_registry
        docname = self.env.docname
        if docname not in gated_registry:
            gated_registry[docname] = {
                "start": [],
                "end": [],
                "sequence": [],
                "msg": [],
                "type": "spice_file",
            }
        gated_registry[self.env.docname]["end"].append(self.lineno)
        gated_registry[self.env.docname]["sequence"].append("E")
        gated_registry[self.env.docname]["msg"].append(
            f"{self.name} at line: {self.lineno}"
        )
        return [spice_file_end_node()]


class spice_simulationStartDirective(spice_simulationDirective):
    """
    A gated directive for spice_simulation

    .. spice_simulation-start:: <spice_file-reference>
       :label:
       :class:
       :hidden:

    This class is a child of spice_simulationDirective so it supports
    all the same options as the base spice_simulation node
    """

    name = "spice_simulation-start"
    spice_simulation_node = spice_simulation_start_node

    def run(self):
        # Initialise Gated Registry (if required)
        if not hasattr(self.env, "sphinx_spice_file_gated_registry"):
            self.env.sphinx_spice_file_gated_registry = {}
        gated_registry = self.env.sphinx_spice_file_gated_registry
        docname = self.env.docname
        if docname not in gated_registry:
            gated_registry[docname] = {
                "start": [],
                "end": [],
                "sequence": [],
                "msg": [],
                "type": "spice_simulation",
            }
        gated_registry[self.env.docname]["start"].append(self.lineno)
        gated_registry[self.env.docname]["sequence"].append("S")
        gated_registry[self.env.docname]["msg"].append(
            f"spice_simulation-start at line: {self.lineno}"
        )
        # Run Parent Methods
        return super().run()


class spice_simulationEndDirective(SphinxDirective):
    """
    A simple gated directive to mark end of spice_simulation

    .. spice_simulation-end::
    """

    name = "spice_simulation-end"

    def run(self):
        # Initialise Gated Registry (if required)
        if not hasattr(self.env, "sphinx_spice_file_gated_registry"):
            self.env.sphinx_spice_file_gated_registry = {}
        gated_registry = self.env.sphinx_spice_file_gated_registry
        docname = self.env.docname
        if docname not in gated_registry:
            gated_registry[docname] = {
                "start": [],
                "end": [],
                "sequence": [],
                "msg": [],
                "type": "spice_simulation",
            }
        gated_registry[self.env.docname]["end"].append(self.lineno)
        gated_registry[self.env.docname]["sequence"].append("E")
        gated_registry[self.env.docname]["msg"].append(
            f"spice_simulation-end at line: {self.lineno}"
        )
        return [spice_simulation_end_node()]
