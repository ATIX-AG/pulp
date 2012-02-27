import sys, os
import rpmUtils
from createrepo import MetaDataGenerator, MetaDataConfig
from createrepo import yumbased, utils

def get_package_xml(pkg):
    
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    po = yumbased.CreateRepoPackage(ts, pkg)

    metadata = {'primary' : po.xml_dump_primary_metadata(),
                'filelists': po.xml_dump_filelists_metadata(),
                'other'   : po.xml_dump_other_metadata(),
               }
    return metadata

def setup_metadata_conf(repodir):
    conf = MetaDataConfig()
    conf.directory = repodir
    conf.update = 1
    conf.database = 1
    conf.verbose = 1
    conf.skip_stat = 1
    return conf
    
def add_package_to_repo(repodir, packages):
    
    mdgen = MetaDataGenerator(setup_metadata_conf(repodir))
    try:
#        mdgen.doPkgMetadata()
        mdgen._setup_old_metadata_lookup()
        packages = mdgen.getFileList(mdgen.package_dir, '.rpm')
        mdgen.pkgcount = len(packages)
        mdgen.openMetadataDocs()
        mdgen.writeMetadataDocs(packages)
        mdgen.closeMetadataDocs()
        mdgen.doRepoMetadata()
        mdgen.doFinalMove()
    except (IOError, OSError), e:
        raise utils.MDError, ('Cannot access/write repodata files: %s') % e
     

if __name__ == '__main__': 
    if len(sys.argv) < 2:
        print "USAGE: python updatemetadata_crapi.py <repodir> <pkgname>"
        sys.exit(0)
   
    repodata_xml = get_package_xml(sys.argv[2])
    print repodata_xml['primary']
    add_package_to_repo(sys.argv[1], [os.path.basename(sys.argv[2])])
