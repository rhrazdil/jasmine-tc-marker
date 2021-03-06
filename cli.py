#!/usr/bin/env python

from os import path
import sys
import re
import yaml

import click
from lxml import etree


class Element:
    def __init__(self, tag, attributes):
        self.tag = tag
        self.attributes = attributes


def parse_params(config, extra_testsuites_poperties):
    # Raise Exception for required config data
    if 'project' not in config:
        raise Exception('project must be defined in config file')
    # Set defaults for optional config data
    if 'keepTestCaseIdentifier' not in config:
        config['keepTestCaseIdentifier'] = True

    if extra_testsuites_poperties:
        extra_properties = extra_testsuites_poperties.split(',')
        for extra_property in extra_properties:
            name, value = extra_property.split(':')
            config['testsuites_properties'].append({'name': name, 'value': value})


def add_children(parent, children):
    added_children = []
    for child in children:
        added_children.append(etree.SubElement(parent, child.tag, child.attributes))
    return added_children


def add_testsuites_properties(xml, data):
    properties = [Element('property', {'name': x['name'], 'value': x['value']}) for x in data]
    testsuites_properties = etree.SubElement(xml.getroot(), 'properties')
    add_children(testsuites_properties, properties)


def process_testcases(testcases, data):
    regex = re.compile(r'ID\({}-\d+\)\s*'.format(data['project']))
    for testcase in testcases:
        found = regex.search(testcase.get('name'))
        if found:
            testcase_id = found.group(0).strip()[3:-1]
            testcase_properties = etree.SubElement(testcase, 'properties')
            add_children(
                testcase_properties,
                [Element('property', {'name': 'polarion-testcase-id', 'value': testcase_id})]
            )
            if not data['keepTestCaseIdentifier']:
                # Remove the identifier from the testcase name
                testcase.set('name', regex.sub('', testcase.get('name')))


@click.command()
@click.option('--report-path', help='path to the XML file with tests report', required=True)
@click.option('--config-file', help='path to configuration file', required=True)
@click.option(
    '--extra-testsuites-properties',
    help='comma separated list of extra testsuites properties in <poperty-name>:<value> format',
    required=False,
)
def main(report_path, config_file, extra_testsuites_properties):
    if path.exists(report_path):
        xml = etree.parse(report_path)
    else:
        sys.exit('Failed to locate xml report file')

    if path.exists(config_file):
        with open(config_file) as fd:
            config = yaml.load(fd, Loader=yaml.FullLoader)
    else:
        sys.exit('Failed to locate configuration file')

    parse_params(config, extra_testsuites_properties)
    # add test suite properties
    add_testsuites_properties(
        xml,
        config['testsuites_properties'] if 'testsuites_properties' in config else [],
    )

    # add and process testcase properties
    testcases = xml.xpath("//testcase")
    process_testcases(testcases, config)

    # write the result to a file
    basepath, filename = path.split(report_path)
    with open(path.join(basepath, 'processed-{}'.format(filename)), 'wb+') as fd:
        fd.write(etree.tostring(xml, pretty_print=True))


if __name__ == '__main__':
    main()
