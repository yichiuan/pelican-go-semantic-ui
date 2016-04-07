# -*- coding: utf-8 -*-

import docutils
from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives, roles, Directive
from pelican import signals
from pelican.readers import RstReader, PelicanHTMLTranslator

class SemanticHTMLTranslator(PelicanHTMLTranslator):

    def visit_literal(self, node):
        classes = node.get('classes', node.get('class', []))
        if 'code' in classes:
            node['classes'] = [cls for cls in classes if cls != 'code']
            self.body.append(self.starttag(node, 'code'))
        elif 'kbd' in classes:
            node['classes'] = [cls for cls in classes if cls != 'kbd']
            self.body.append(self.starttag(node, 'kbd'))
        else:
            self.body.append(self.starttag(node, 'code'))

    def depart_literal(self, node):
        classes = node.get('classes', node.get('class', []))
        if 'code' in classes:
            self.body.append('</code>\n')
        elif 'kbd' in classes:
            self.body.append('</kbd>\n')
        else:
            self.body.append('</code>\n')

    # remove nested section

    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    def visit_title(self, node):
        check_id = 0
        close_tag = '</p>\n'
        if isinstance(node.parent, nodes.topic):
            self.body.append(
                  self.starttag(node, 'p', '', CLASS='topic-title first'))
        elif isinstance(node.parent, nodes.sidebar):
            self.body.append(
                  self.starttag(node, 'p', '', CLASS='sidebar-title'))
        elif isinstance(node.parent, nodes.Admonition):
            self.body.append(
                  self.starttag(node, 'p', '', CLASS='admonition-title'))
        elif isinstance(node.parent, nodes.table):
            self.body.append(
                  self.starttag(node, 'caption', ''))
            close_tag = '</caption>\n'
        elif isinstance(node.parent, nodes.document):
            self.body.append(self.starttag(node, 'h1', '', CLASS='title'))
            close_tag = '</h1>\n'
            self.in_document_title = len(self.body)
        else:
            assert isinstance(node.parent, nodes.section)
            h_level = self.section_level + self.initial_header_level - 1

            # Add id for internal links
            if 'ids' in node.parent:
                node['ids'] = node.parent['ids']

            atts = {}
            if (len(node.parent) >= 2 and
                isinstance(node.parent[1], nodes.subtitle)):
                atts['CLASS'] = 'with-subtitle'
            self.body.append(
                  self.starttag(node, 'h%s' % h_level, '', **atts))
            atts = {}
            if node.hasattr('refid'):
                atts['class'] = 'toc-backref'
                atts['href'] = '#' + node['refid']
            if atts:
                self.body.append(self.starttag({}, 'a', '', **atts))
                close_tag = '</a></h%s>\n' % (h_level)
            else:
                close_tag = '</h%s>\n' % (h_level)
        self.context.append(close_tag)

    def visit_enumerated_list(self, node):
        atts = {}
        if 'start' in node:
            atts['start'] = node['start']
        self.body.append(self.starttag(node, 'ol', **atts))

    def depart_enumerated_list(self, node):
        self.body.append('</ol>\n')

    def visit_bullet_list(self, node):
        atts = {}
        self.body.append(self.starttag(node, 'ul', **atts))

    def depart_bullet_list(self, node):
        self.body.append('</ul>\n')


    def visit_definition_list(self, node):
        self.body.append(self.starttag(node, 'dl'))

    def visit_transition(self, node):
        self.body.append(self.starttag(node, 'hr'))

    # Clean Tables and HTML5 specs
    # remove colgroup

    def visit_table(self, node):
        classes = [cls.strip(' \t\n')
                   for cls in self.settings.table_style.split(',')]
        tag = self.starttag(node, 'table', CLASS=' '.join(classes))
        self.body.append(tag)

    def depart_table(self, node):
        self.body.append('</table>\n')

    def visit_tgroup(self, node):
        node.stubs = []

    def visit_thead(self, node):
        self.body.append(self.starttag(node, 'thead'))

    def visit_tbody(self, node):
        self.body.append(self.starttag(node, 'tbody'))

    def visit_field_list(self, node):
        self.context.append((self.compact_field_list, self.compact_p))
        self.compact_p = None
        if 'compact' in node['classes']:
            self.compact_field_list = True
        elif (self.settings.compact_field_lists
              and 'open' not in node['classes']):
            self.compact_field_list = True
        if self.compact_field_list:
            for field in node:
                field_body = field[-1]
                assert isinstance(field_body, nodes.field_body)
                children = [n for n in field_body
                            if not isinstance(n, nodes.Invisible)]
                if not (len(children) == 0 or
                        len(children) == 1 and
                        isinstance(children[0],
                                   (nodes.paragraph, nodes.line_block))):
                    self.compact_field_list = False
                    break
        self.body.append(self.starttag(node, 'table',
                                       CLASS='docutils field-list'))
        self.body.append('<tbody>\n')

    def visit_footnote(self, node):
        self.body.append(self.starttag(node, 'table',
                                       CLASS='docutils footnote'))
        self.body.append('<tbody>\n'
                         '<tr>')
        self.footnote_backrefs(node)

    def visit_citation(self, node):
        self.body.append(self.starttag(node, 'table',
                                       CLASS='docutils citation'))
        self.body.append('<tbody>\n'
                         '<tr>')
        self.footnote_backrefs(node)


class SemanticRSTReader(RstReader):

    def _get_publisher(self, source_path):
        extra_params = {'initial_header_level': '2',
                        'syntax_highlight': 'short',
                        'input_encoding': 'utf-8',
                        'exit_status_level': 2,
                        'embed_stylesheet': False}
        user_params = self.settings.get('DOCUTILS_SETTINGS')
        if user_params:
            extra_params.update(user_params)

        pub = docutils.core.Publisher(
            source_class=self.FileInput,
            destination_class=docutils.io.StringOutput)
        pub.set_components('standalone', 'restructuredtext', 'html')
        pub.writer.translator_class = SemanticHTMLTranslator
        pub.process_programmatic_settings(None, extra_params, None)
        pub.set_source(source_path=source_path)
        pub.publish(enable_exit_status=True)
        return pub

def keyboard_role(name, rawtext, text, lineno, inliner,
                  options={}, content=[]):
    """
        This function creates an inline console input block
        overrides the default behaviour of the kbd role
        *usage:*
            :kbd:`<your code>`
        *Example:*
            :kbd:`<section>`
        This code is not highlighted
    """
    new_element = nodes.literal(rawtext, text)
    new_element.set_class('kbd')

    return [new_element], []

def register_roles():
    rst.roles.register_local_role('kbd', keyboard_role)

def add_reader(readers):
    readers.reader_classes['rst'] = SemanticRSTReader


def register():
    register_roles()
    signals.readers_init.connect(add_reader)