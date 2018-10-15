"""Tests for the utility functions."""

import os
import lxml.etree
import siptools.utils as utils


def test_encode_path():
    """Tests for the encode_path function."""

    encoded_path = utils.encode_path('tests/testpath')
    assert encoded_path == 'tests%2Ftestpath'

    encoded_path = utils.encode_path(
        'tests/testpath', suffix='-testsuffix', prefix='testprefix-'
    )
    assert encoded_path == 'testprefix-tests%2Ftestpath-testsuffix'

    encoded_path = utils.encode_path(u't\u00e4sts/t\u00f8stpath')
    assert encoded_path == u't%C3%A4sts%2Ft%C3%B8stpath'


def test_decode_path():
    """Tests for the decode_path function."""

    decoded_path = utils.decode_path('tests%2Ftestpath')
    assert decoded_path == 'tests/testpath'

    decoded_path = utils.decode_path(
        'tests%2Ftestpath-testsuffix', suffix='-testsuffix'
    )
    assert decoded_path == 'tests/testpath'

    decoded_path = utils.decode_path('t%C3%A4sts%2Ft%C3%B8stpath')
    assert decoded_path == u't\u00e4sts/t\u00f8stpath'


def test_create_techmdfile(testpath):
    """Test write_md function. Pass a dummy XML element to the
    function and check that XML file with correct filename is created to
    workspace. Check that XML file contains expected elements.
    """

    md_creator = utils.TechmdCreator(testpath)

    sample_data = lxml.etree.Element('sampleData')
    md_creator.write_md(sample_data, 'NISOIMG', '2.0')

    element_tree = lxml.etree.parse(
        os.path.join(
            testpath,
            '455752263d67f67402b0dc9e7119e5b3-NISOIMG-techmd.xml'
        )
    )

    # The file should contain one techmd element
    techmd_elements = element_tree.xpath(
        '/mets:mets/mets:amdSec/mets:techMD',
        namespaces={"mets": "http://www.loc.gov/METS/"}
    )
    assert len(techmd_elements) == 1

    # The techMD element should contain one sampleData element wrapped in
    # mdWrap and xmlData elements
    sample_data_elements \
        = techmd_elements[0].xpath(
            '//mets:mdWrap/mets:xmlData/sampleData',
            namespaces={"mets": "http://www.loc.gov/METS/"}
        )
    assert len(sample_data_elements) == 1


def test_add_techmdreference(testpath):
    """Test add_reference function. Calls function two times and
    write the techmdreference file.
    """

    md_creator = utils.TechmdCreator(testpath)

    md_creator.add_reference('abcd1234', 'path/to/file1')
    md_creator.add_reference('abcd1234', 'path/to/file2')

    md_creator.write_references()

    # Read created file. Reference should be found for both files
    etree = lxml.etree.parse(os.path.join(testpath, 'techmd-references.xml'))
    reference = etree.xpath(
        '/techmdReferences/techmdReference[@file="path/to/file1"]'
    )
    assert reference[0].text == 'abcd1234'
    reference = etree.xpath(
        '/techmdReferences/techmdReference[@file="path/to/file2"]'
    )
    assert reference[0].text == 'abcd1234'


def test_copy_etree():
    """Test that copy_etree creates a new lxml.etree 
    instance with identical data.
    """
    etree1 = lxml.etree.parse("tests/data/sample_techmd-references.xml")
    etree2 = utils.copy_etree(etree1)

    assert id(etree1) != id(etree2)
    assert lxml.etree.tostring(etree1) == lxml.etree.tostring(etree2)
