"""Tests for :mod:`siptools.scripts.premis_event` module"""
from __future__ import unicode_literals

import os

import pytest

import lxml.etree as ET
from siptools.scripts import premis_event


def test_premis_event_ok(testpath, run_cli):
    """Test that main function produces event.xml and agent.xml files with
    correct elements.
    """
    run_cli(premis_event.main, [
        'creation',
        '2016-10-13T12:30:55',
        '--event_target', 'tests/data/structured',
        '--event_detail', 'Testing',
        '--event_outcome', 'success',
        '--event_outcome_detail', 'Outcome detail',
        '--workspace', testpath,
        '--agent_name', 'Demo Application',
        '--agent_type', 'software'
    ])

    # Read output files
    event_xml = ET.parse(
        os.path.join(
            testpath,
            '4a4a5d87842b048eef1c59ab3fef286d-PREMIS%3AEVENT-amd.xml')
    ).getroot()
    agent_xml = ET.parse(
        os.path.join(
            testpath,
            'd4e928570d571cb1ba79e3b7ba23cd89-PREMIS%3AAGENT-amd.xml')
    ).getroot()

    namespaces = {'mets': 'http://www.loc.gov/METS/',
                  'premis': 'info:lc/xmlns/premis-v2'}

    # Both output files should have one amdSec element
    assert len(event_xml.findall('mets:amdSec', namespaces=namespaces)) == 1
    assert len(agent_xml.findall('mets:amdSec', namespaces=namespaces)) == 1

    # Check thait event.xml contains required elements with correct content
    for element, content in (
            (".//premis:eventType", 'creation'),
            (".//premis:eventDateTime", '2016-10-13T12:30:55'),
            (".//premis:eventDetail", 'Testing'),
            (".//premis:eventOutcome", 'success'),
            (".//premis:eventOutcomeDetailNote", 'Outcome detail')
    ):
        assert event_xml.findall(element, namespaces=namespaces)[0].text \
            == content

    # Check thait agent.xml contains required elements with correct content
    for element, content in (
            (".//premis:agentName", 'Demo Application'),
            (".//premis:agentType", 'software')
    ):
        assert agent_xml.findall(element, namespaces=namespaces)[0].text \
            == content

    # event.xml file should contain link to agent-element in agent.xml file
    assert \
        event_xml.findall('.//premis:linkingAgentIdentifierValue',
                          namespaces=namespaces)[0].text \
        == \
        agent_xml.findall('.//premis:agentIdentifierValue',
                          namespaces=namespaces)[0].text


def test_amd_links_root(testpath, run_cli):
    """Tests that premis_event script writes reference links correctly
    to the md-references file.
    """
    run_cli(premis_event.main, [
        'creation',
        '2016-10-13T12:30:55',
        '--event_detail', 'Testing',
        '--event_outcome', 'success',
        '--workspace', testpath
    ])

    ref = os.path.join(testpath, 'md-references.xml')
    assert os.path.isfile(ref)

    root = ET.parse(ref).getroot()
    dir_ref = root.xpath("/mdReferences/mdReference")[0].get('directory')
    assert dir_ref == '.'


def test_amd_links_file(testpath, run_cli):
    """Tests that premis_event script writes reference links correctly
    to the md-references file with a proper file target.
    """
    target = 'tests/data/test_import.pdf'
    run_cli(premis_event.main, [
        'creation',
        '2016-10-13T12:30:55',
        '--event_detail', 'Testing',
        '--event_outcome', 'success',
        '--workspace', testpath,
        '--event_target', target
    ])

    ref = os.path.join(testpath, 'md-references.xml')
    assert os.path.isfile(ref)

    root = ET.parse(ref).getroot()
    dir_ref = root.xpath("/mdReferences/mdReference")[0].get('file')
    assert dir_ref == target


def test_amd_links_dir(testpath, run_cli):
    """Tests that premis_event script writes reference links correctly
    to the md-references file with a directory target.
    """
    target = 'tests/data'
    run_cli(premis_event.main, [
        'creation',
        '2016-10-13T12:30:55',
        '--event_detail', 'Testing',
        '--event_outcome', 'success',
        '--workspace', testpath,
        '--event_target', target
    ])

    ref = os.path.join(testpath, 'md-references.xml')
    assert os.path.isfile(ref)

    root = ET.parse(ref).getroot()
    dir_ref = root.xpath("/mdReferences/mdReference")[0].get('directory')
    assert dir_ref == target


def test_premis_event_fail(testpath, run_cli):
    """Test that main function raises `SystemExit` if `event_outcome`
    parameter is incorrect."""

    result = run_cli(premis_event.main, [
        'creation', '2016-10-13T12:30:55',
        '--event_detail', 'Testing',
        '--event_outcome', 'nonsense',
        '--event_outcome_detail', 'Outcome detail',
        '--workspace', testpath
    ], success=False)
    assert isinstance(result.exception, SystemExit)


@pytest.mark.parametrize((
    'base_path', 'event_target', 'directory', 'event_file'), [
        # No base_path, target is directory
        ('.', 'tests/data/structured', 'tests/data/structured', None),
        # No base_path or event_target, target is package root
        ('.', None, '.', None),
        # No event_target, target is still package root
        ('tests/data', None, '.', None),
        # Target is a directory
        ('tests/data/', 'structured', 'structured', None),
        # Target is a file
        ('tests/data/',
         'structured/Access and use rights files/access_file.txt', None,
         'structured/Access and use rights files/access_file.txt'),
        ])
def test_event_target_path(base_path, event_target, directory, event_file):
    """Tests the event_target_path function."""
    (ev_directory, ev_file) = premis_event.event_target_path(
        base_path, event_target)

    assert ev_directory == directory
    assert ev_file == event_file


def test_invalid_event_target_path():
    """Tests that event_target_path raises IOError if given
    event_target path doesn't exist.
    """
    with pytest.raises(IOError):
        premis_event.event_target_path('.', 'foo/bar')


def test_create_premis_event_file_ok(testpath):
    """Test that create_premis_event_file function produces event.xml file with
    correct elements.
    """

    (file_path, event_xml) = premis_event.create_premis_event_file(
        testpath,
        'creation',
        '2016-10-13T12:30:55',
        'Testing',
        'success',
        'Outcome detail')

    assert file_path == os.path.join(testpath, 'creation-event-amd.xml')

    namespaces = {'mets': 'http://www.loc.gov/METS/',
                  'premis': 'info:lc/xmlns/premis-v2'}

    # Should have one amdSec element
    assert len(event_xml.findall('mets:amdSec', namespaces=namespaces)) == 1

    # Check thait event.xml contains required elements with correct content
    for element, content in (
            (".//premis:eventType", 'creation'),
            (".//premis:eventDateTime", '2016-10-13T12:30:55'),
            (".//premis:eventDetail", 'Testing'),
            (".//premis:eventOutcome", 'success'),
            (".//premis:eventOutcomeDetailNote", 'Outcome detail')
    ):
        assert event_xml.findall(
            element, namespaces=namespaces)[0].text == content


def test_create_premis_agent_file_ok(testpath):
    """Test that create_premis_agent_file function produces agent.xml file with
    correct elements.
    """

    (file_path, agent_xml) = premis_event.create_premis_agent_file(
        testpath,
        'event-type',
        'Demo Application',
        'software',
        'Agent Identifier')

    assert file_path == os.path.join(testpath, 'event-type-agent-amd.xml')

    namespaces = {'mets': 'http://www.loc.gov/METS/',
                  'premis': 'info:lc/xmlns/premis-v2'}

    # Should have one amdSec element
    assert len(agent_xml.findall('mets:amdSec', namespaces=namespaces)) == 1

    # Check thait agent.xml contains required elements with correct content
    for element, content in (
            (".//premis:agentName", 'Demo Application'),
            (".//premis:agentType", 'software')
    ):
        assert agent_xml.findall(element, namespaces=namespaces)[0].text \
            == content
