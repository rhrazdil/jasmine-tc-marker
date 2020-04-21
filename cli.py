from os import path
import re
import yaml

import click
from lxml import etree


class Element:
    def __init__(self, tag, attributes):
        self.tag = tag
        self.attributes = attributes


def check_config(config):
    if 'project' not in config:
        raise Exception('project must be defined in config file')


def add_children(parent, children):
    added_children = []
    for child in children:
        added_children.append(etree.SubElement(parent, child.tag, child.attributes))
    return added_children


def add_testsuites_properties(xml, data, keep_testcase_identifiers):
    properties = [Element('property', {'name': x['name'], 'value': x['value']}) for x in data]
    testsuites_properties = etree.SubElement(xml.getroot(), 'properties')
    add_children(testsuites_properties, properties)


def process_testcases(testcases, project):
    regex = re.compile(r'ID\({}-\d+\)\s*'.format(project))
    for testcase in testcases:
        found = regex.search(testcase.get('name'))
        if found:
            testcase_id = found.group(0).strip()[3:-1]
            testcase_properties = etree.SubElement(testcase, 'properties')
            add_children(
                testcase_properties,
                [Element('property', {'name': 'polarion-testcase-id', 'value': testcase_id})]
            )
            # Remove the identifier from the testcase name
            testcase.set('name', regex.sub('', testcase.get('name')))


@click.command()
@click.option('--report-path', help='path to the XML file with tests report', required=True)
@click.option('--config-file', help='path to configuration file', required=True)
def main(report_path, config_file):
    xml = etree.parse(report_path)
    with open(config_file) as fd:
        data = yaml.load(fd, Loader=yaml.FullLoader)
    check_config(data)

    # add test suite properties
    add_testsuites_properties(
        xml,
        data['testsuites_properties'] if 'testsuites_properties' in data else [],
        data['keepTestCaseIdentifier'] if 'keepTestCaseIdentifier' in data else True,
    )

    # add and process testcase properties
    testcases = xml.xpath("//testcase")
    process_testcases(testcases, data['project'])

    # write the result to a file
    basepath, filename = path.split(report_path)
    with open(path.join(basepath, 'processed-{}'.format(filename)), 'wb+') as fd:
        fd.write(etree.tostring(xml, pretty_print=True))


if __name__ == '__main__':
    main()
