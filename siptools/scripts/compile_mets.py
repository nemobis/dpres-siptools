"""Command line tool for creating METS document and copying files to workspace
directory.
"""
from __future__ import unicode_literals

import datetime
import os
import sys
import uuid
from shutil import copyfile

import click
import six

import lxml.etree
import mets
import xml_helpers.utils as xml_utils
from scandir import scandir
from siptools.utils import get_objectlist
from siptools.xml.mets import (METS_CATALOG, METS_PROFILE, METS_SPECIFICATION,
                               NAMESPACES, RECORD_STATUS_TYPES, mets_extend)

click.disable_unicode_literals_warning = True


@click.command()
@click.argument('mets_profile', type=click.Choice(METS_PROFILE))
@click.argument('organization_name', type=str)
@click.argument('contractid', type=click.UUID)
@click.option('--workspace',
              type=click.Path(exists=True),
              default='./workspace',
              metavar='<WORKSPACE PATH>',
              help='Workspace directory. Defaults to "./workspace".')
@click.option('--base_path',
              metavar='<BASE PATH>',
              type=click.Path(exists=True),
              default='.',
              help='Base path of the digital objects.')
@click.option('--objid', type=str,
              default=six.text_type(uuid.uuid4()),
              metavar='<OBJID>',
              help='Unique identifier for the package')
@click.option('--label',
              type=str,
              metavar='<LABEL>',
              help='Short description of the information package')
@click.option('--contentid',
              type=str,
              metavar='<CONTENTID>',
              help='Identifier for content, useful for the case where '
                   'content is divided in several SIPs.')
@click.option('--create_date',
              type=str,
              default=datetime.datetime.utcnow().isoformat(),
              metavar='<CREATION DATE>',
              help='SIP create datetime formatted as '
                   'yyyy-mm-ddThh:mm:ss. Defaults to current time.')
@click.option('--last_moddate',
              type=str,
              metavar='<LAST MODIFICATION DATE>',
              help='Last modification datetime formatted as '
                   'yyyy-mm-ddThh:mm:ss')
@click.option('--record_status',
              type=click.Choice(RECORD_STATUS_TYPES),
              default='submission',
              metavar='<RECORD STATUS>',
              help='Record status. Defaults to "submission".')
@click.option('--clean',
              is_flag=True,
              help='Remove partial METS documents from workspace directory')
@click.option('--copy_files',
              is_flag=True,
              help='Copy digital objects from base path to workspace')
@click.option('--stdout',
              is_flag=True,
              help='Print output to stdout.')
@click.option('--packagingservice',
              type=str,
              metavar='<PACKAGING SERVICE>',
              help='If defined, add packaging service as CREATOR '
                   'agent to METS Header.')
def main(mets_profile, organization_name, contractid, objid, label,
         contentid, create_date, last_moddate, record_status, workspace,
         clean, copy_files, base_path, stdout, packagingservice):
    """Merge partial METS documents in workspace directory into
    one METS document.

    \b
    METS_PROFILE: METS profile.
    ORGANIZATION_NAME: Creator name (organization)
    CONTRACTID: Contract ID given by the Digital Preservation Service
    """
    compile_mets(
        mets_profile, organization_name, contractid, objid, label, contentid,
        create_date, last_moddate, record_status, workspace, clean, copy_files,
        base_path, stdout, packagingservice
    )
    return 0


def compile_mets(mets_profile, organization_name, contractid, objid=None,
                 label=None, contentid=None, create_date=None,
                 last_moddate=None, record_status="submission",
                 workspace="./workspace", clean=False, copy_files=False,
                 base_path=".", stdout=False, packagingservice=None):
    """Merge partial METS documents in workspace directory into
    one METS document."""
    contract = "urn:uuid:%s" % contractid

    if not objid:
        objid = six.text_type(uuid.uuid4())

    if not create_date:
        create_date = datetime.datetime.utcnow().isoformat()

    mets_document = create_mets(
        workspace,
        mets_attributes={'PROFILE': mets_profile,
                         'OBJID': objid,
                         'LABEL': label,
                         "CONTENTID": contentid,
                         "CONTRACTID": contract},
        metshdr_attributes={"CREATEDATE": create_date,
                            "LASTMODDATE": last_moddate,
                            "RECORDSTATUS": record_status},
        organization=organization_name,
        packagingservice=packagingservice
    )

    if stdout:
        print(xml_utils.serialize(mets_document.getroot()))

    output_file = os.path.join(workspace, 'mets.xml')

    if not os.path.exists(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))

    with open(output_file, 'wb+') as outfile:
        outfile.write(xml_utils.serialize(mets_document.getroot()))

    print("compile_mets created file: %s" % output_file)

    if copy_files:
        copy_objects(workspace, base_path)
        print("compile_mets copied objects from %s to workspace" % base_path)

    if clean:
        clean_metsparts(workspace)
        print("compile_mets cleaned work files from workspace")


def create_mets(workspace, mets_attributes, metshdr_attributes,
                organization, packagingservice=None):
    """Creates METS document element tree. Looks for files with prefix
    "-amd.xml", "dmdsec.xml", "structmap.xml", "filesec.xml", and
    "rightsmd.xml" from workspace and merges the dmdSec,
    amdSec, fileSec, and structMap elements (one element from each file) into
    one METS document. Also metsHdr element is created and included in
    document.

    :param workspace: path to directory where files are searched
    :param dict mets_attributes: attributes of mets element: "PROFILE",
                                 "OBJID", "LABEL", "CONTENTID", and
                                 "CONTRACTID"
    :param dict metshdr_attributes: attributes of metsHdr element:
                                    "CREATEDATE", "LASTMODDATE" and
                                    "RECORDSTATUS"
    :param organization: name of CREATOR agent
    :param packagingservice: Add ``packagingservice`` as CREATOR agent.
                             ``organization`` is used as ARCHIVIST agent.
    :returns: METS document ElementTree object
    """
    # Create list of agent elements
    if packagingservice:
        agents = [mets.agent(organization, agent_role='ARCHIVIST')]
        agents.append(mets.agent(packagingservice,
                                 agent_type='OTHER',
                                 agent_role='CREATOR',
                                 othertype='SOFTWARE'))
    else:
        agents = [mets.agent(organization, agent_role='CREATOR')]

    # Create mets header
    metshdr = mets.metshdr(metshdr_attributes["CREATEDATE"],
                           metshdr_attributes["LASTMODDATE"],
                           metshdr_attributes["RECORDSTATUS"],
                           agents)

    # Collect elements from workspace XML files
    elements = []
    for entry in scandir(workspace):
        if entry.name.endswith(('-amd.xml', 'dmdsec.xml',
                                'structmap.xml', 'filesec.xml',
                                'rightsmd.xml')) and entry.is_file():
            element = lxml.etree.parse(entry.path).getroot()[0]
            elements.append(element)

    elements = mets.merge_elements('{%s}amdSec' % NAMESPACES['mets'], elements)
    elements.sort(key=mets.order)

    # Create METS element
    mets_element = mets.mets(METS_PROFILE[mets_attributes["PROFILE"]],
                             objid=mets_attributes["OBJID"],
                             label=mets_attributes["LABEL"],
                             namespaces=NAMESPACES)
    mets_element = mets_extend(mets_element,
                               METS_CATALOG,
                               METS_SPECIFICATION,
                               mets_attributes["CONTENTID"],
                               mets_attributes["CONTRACTID"])
    mets_element.append(metshdr)
    for element in elements:
        mets_element.append(element)
    lxml.etree.cleanup_namespaces(mets_element)

    return lxml.etree.ElementTree(mets_element)


def clean_metsparts(path):
    """Clean mets parts from workspace
    """
    for root, _, files in os.walk(path, topdown=False):
        for name in files:
            if (name.endswith(('-amd.xml', 'dmdsec.xml', 'structmap.xml',
                               'filesec.xml', 'rightsmd.xml',
                               'md-references.xml',
                               '-scraper.pkl'))):
                os.remove(os.path.join(root, name))


def copy_objects(workspace, data_dir):
    """Copy digital objects to workspace
    """
    files = get_objectlist(workspace)
    for source in files:
        target = os.path.join(workspace, source)
        if not os.path.exists(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))
        copyfile(os.path.join(data_dir, source), target)


if __name__ == '__main__':
    RETVAL = main()  # pylint: disable=no-value-for-parameter
    sys.exit(RETVAL)
