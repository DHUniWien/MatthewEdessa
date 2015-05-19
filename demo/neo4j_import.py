__author__ = 'tla'

import argparse
import re
from py2neo import authenticate, Graph, Node, Relationship
from lxml import etree


class TraditionImport:

    tradition = None

    def __init__(self, n4user, n4pass):
        authenticate('localhost:7474', n4user, n4pass)
        self.db = Graph()

    def from_graphml(self, filename, name=None):
        """Import a Stemmaweb GraphML file into Neo4J."""
        # Get the database connection
        # Get the XML tree
        graphml = etree.parse(filename).getroot()
        property_keys = self._extract_tradition_attributes(graphml)

        # Identify the main graph and the relationship graph.
        main_graph = None
        relationship_graph = None
        for graph_el in graphml.iter(self.qn('graph')):
            if graph_el.get('id') == 'relationships':
                relationship_graph = graph_el
            else:
                main_graph = graph_el

        # Make the tradition node with its properties. But add the name
        # as a property key.
        namekey = etree.SubElement(main_graph, self.qn('data'))
        namekey.set('key', 'name')
        if name:
            namekey.text = name
        else:
            namekey.text = main_graph.get('id')

        # TODO I really want this entire thing created in one transaction.
        self.tradition = self._make_node(main_graph, 'graph', property_keys)

        # Now do the same for each node.
        startnode = None   # to attach it to the tradition
        nodes_by_xmlid = {}
        for node_el in main_graph.iter(self.qn('node')):
            reading = self._make_node(node_el, 'node', property_keys)
            if reading.properties['is_start']:
                startnode = reading
            nodes_by_xmlid[node_el.get('id')] = reading
        # Link the tradition to its start node
        self.db.create(Relationship(self.tradition, 'COLLATION', startnode))

        # Now run through the edges, collecting them into a unique edge for
        # each source/target pair. This will also tell us the witnesses in the
        # text, which should be linked to the tradition.
        self._make_edges(main_graph, property_keys, nodes_by_xmlid)

        # Now collect the edges for the relationship graph. We can safely
        # assume node definitions are identical.
        self._make_relationship_edges(relationship_graph, property_keys, nodes_by_xmlid)

        # Write the tradition and all its information to the DB in a single transaction.
        return self.tradition

    def _extract_tradition_attributes(self, root_el):
        """Read the <key> elements in teh GraphML to get the possible properties."""
        properties = {
            'graph': {},
            'node': {},
            'edge': {}
        }
        datatypes = {'string': 'str', 'boolean': 'bool', 'int':'int'}
        for propkey in root_el.iter(self.qn('key')):
            pwhat = propkey.get('for')
            pname = propkey.get('attr.name')
            ptype = propkey.get('attr.type')
            pid = propkey.get('id')
            properties[pwhat][pid] = (pname, datatypes[ptype])
        # Add 'name' as a graph property
        properties['graph']['name'] = ('name', 'str')
        return properties

    def _make_node(self, el, element_type, property_keys):
        element_labels = {
            'graph': 'TRADITION',
            'node': 'READING',
        }
        element_properties = self._get_properties(el, element_type, property_keys)
        obj, = self.db.create(Node(element_labels[element_type], **element_properties))
        return obj

    def _make_edges(self, graph, property_keys, all_nodes):
        sequence_list = {}
        # Go through all the edges in the GraphML, collecting up the witnesses
        # between each pair of nodes
        sigla_seen = {}
        for edge_el in graph.iter(self.qn('edge')):
            props = self._get_properties(edge_el, 'edge', property_keys)
            source = edge_el.get('source')
            target = edge_el.get('target')
            wit = props['witness']
            sigla_seen[wit] = 1
            if 'extra' in props:
                wit += props['extra']
            if source in sequence_list:
                if target in sequence_list[source]:
                    sequence_list[source][target].append(props['witness'])
                else:
                    sequence_list[source][target] = [props['witness']]
            else:
                sequence_list[source] = {target: [props['witness']]}
        # Make a node for each witness
        for w in sigla_seen.keys():
            witness, = self.db.create(Node('WITNESS', sigil=w))
            self.db.create(Relationship(self.tradition, 'HAS_WITNESS', witness))
        # Now make a single relationship for each source/target pair
        for source in sequence_list:
            for target in sequence_list[source]:
                rfrom = all_nodes[source]
                rto = all_nodes[target]
                rwits = sequence_list[source][target]
                self.db.create(Relationship(rfrom, 'SEQUENCE', rto, witnesses=rwits))
        return

    def _make_relationship_edges(self, graph, property_keys, all_nodes):
        for edge_el in graph.iter(self.qn('edge')):
            props = self._get_properties(edge_el, 'edge', property_keys)
            source = all_nodes[edge_el.get('source')]
            target = all_nodes[edge_el.get('target')]
            self.db.create(Relationship(source, 'RELATED', target, **props))
        return

    def _get_properties(self, el, element_type, property_keys):
        element_properties = {}
        for dataval in el.iterfind(self.qn('data')):
            dkey = dataval.get('key')
            if dkey in property_keys[element_type]:
                prop = property_keys[element_type][dkey]
                dval = getattr(__builtins__, prop[1])(dataval.text)
                element_properties[prop[0]] = dval
            else:
                raise InputError("Unknown property %s defined for %s node" % (dkey, element_type))
        return element_properties

    def qn(self, x):
        return '{http://graphml.graphdrawing.org/xmlns}%s' % x

    def from_plaintext(self, filename, name='Some text', encoding='utf-8', sep_char=' ', baselabel='base text'):
        with open(filename, encoding=encoding) as fh:
            textlines = fh.readlines()
        split_pattern = sep_char
        if sep_char is ' ':
            split_pattern = '\s+'
        words = re.split(split_pattern, ' '.join([line.rstrip() for line in textlines]))
        # Make the tradition node
        tradition = Node('TRADITION', name=name, sep_char=sep_char, baselabel=baselabel)
        start = Node('READING', is_start=True)
        self.db.create(tradition, start, Relationship(tradition, 'COLLATION', start))
        prior = start
        for w in words:
            # Make the word nodes
            reading = Node('READING', text=w, is_lemma=True, is_common=True)
            # Link them up in sequence
            self.db.create(reading, Relationship(prior, 'SEQUENCE', reading, witnesses=[baselabel]))
            prior = reading
        # Make the end node
        (end, endrel) = self.db.create(Node('READING', is_end=True), Relationship(tradition, 'HAS_END', 0))
        self.tradition = tradition
        return tradition


class InputError(Exception):
    pass

if __name__ == '__main__':
    argp = argparse.ArgumentParser(description="Parse a file into the graph")
    argp.add_argument('file')
    argp.add_argument('-f', choices=['graphml', 'plaintext'], required=True)
    argp.add_argument('-n', default=None)
    options = argp.parse_args()

    importer = TraditionImport('neo4j', 'Nothing')
    method = 'from_%s' % options.f
    parsed_tradition = getattr(importer, method)(options.file, options.n)
    print("Made tradition %s" % parsed_tradition.properties['name'])