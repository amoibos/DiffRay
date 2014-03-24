'''
Created on 05.09.2013

@author: pinkflawd
'''

from __future__ import print_function
import logging.config
from optparse import OptionParser
import os
import re
import sys
import traceback

import Diffing.Info
import Parsing.Library


def main():
    
    '''
    MAIN CLASS
    command line option parsing
    exception catching
    '''
    
    try:
        logging.config.fileConfig(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), '..', 'conf', 'logger.conf'))
        log = logging.getLogger('Main')
    except IOError:
        # here could go some configuration of a default logger -- me too lazy
        # additionally one could add a cmdline option for loggint to a file instead of stdout -- me too lazy
        print("Error, logger.conf not found or broken. Check on http://docs.python.org/2/howto/logging.html what to do.")
        sys.exit(1)
    
    parser = OptionParser()
       
    ### Parsing
    parser.add_option("-d", "--dirparse", dest="directory", help="The directory which contains EITHER c or lst files for ONE os! Needs OS and type option.")
    parser.add_option("-n", "--no-flush", action="store_true", dest="noflush", help="Continue parsing without flushing existing function info - mb the app crashed before..")
    parser.add_option("-p", "--parse", dest="filename", help="The file to parse, needs the OS option and the type option too")
    parser.add_option("-o", "--os", dest="os", help="OS the Library belongs to, Win7 or Win8")
    parser.add_option("-t", "--type", dest="ftype", help="Type of file to parse - .c or .lst")
    
    ### Maintenance
    parser.add_option("-f", "--flushall", action="store_true", dest="flush", help="Flush the Database Scheme")
    parser.add_option("-c", "--create-scheme", action="store_true", dest="createall", help="(Re)Create Database Scheme (same as flushall option)")
    parser.add_option("-u", "--update-sigs", action="store_true", dest="updatesigs", help="Flushes the signature table and re-reads the signatures.conf for update")
    parser.add_option("-m", "--print-mappings", action="store_true", dest="printmappings", help="Prints the Mappings in the signature table")
    
    ### Database
    parser.add_option("-b", "--backend", dest="database", help="Database backend to use, currently supported: sqlite (default), mssql - use mssql/MSSQL or sqlite/SQLITE !!!")
        
    ### Diffing
    parser.add_option("-s", "--search_libs", dest="libname", help="Provide a library name (without .dll ending!!) to be searched in the DB, gives you the IDs you need for diffing!")
    parser.add_option("-a", "--lib_all_info", dest="lib_allinfo", help="Takes one libid as argument and prints all hit information in csv format")
    parser.add_option("-i", "--diff", action="store_true", dest="diff", help="Diffing of two libraries, needs arguments lib1 and lib2, lib1 should be win7 as difflib, lib2 for win8 as baselib")
    parser.add_option("-1", "--lib_1", dest="lib_one", help="Difflib for diffing - Win7 goes here")
    parser.add_option("-2", "--lib_2", dest="lib_two", help="Baselib for diffing - Win8 goes here")
    parser.add_option("-e", "--diff_byname", dest="diffbyname", help="Diff two libs by name, two-sided, provide a libname like advapi32.c. CAUTION: Tool aborts when more than 2 libs are matched and DOES NOT VERIFY if the two difflibs belong together.")
    
    options, args = parser.parse_args()
    
    ### OPTION backend ###
    
    if options.database.lower() in "mssql":
        database = "MSSQL"
        import Database.MSSqlDB
        db = Database.MSSqlDB.MSSqlDB()
    else:
        database = "SQLITE"
        import Database.SQLiteDB
        db = Database.SQLiteDB.SQLiteDB()

    ### OPTION parse ###
 
    if None not in (options.filename, options.directory) and None not in (options.os, options.ftype):
        
        try:
            
            if options.directory is not None:
                _, _, lib_files = os.walk(options.directory).next()
            else:
                lib_files = list(options.filename)
                
            for lib_file in lib_files:        
                lib = Parsing.Library.Library(lib_file, options.os, options.ftype, database)
                
                # if lib exists - flush functions
                # if lib exists and no-flush active - continue
                if (lib.existant and options.noflush is None) or not lib.existant:
                    lib.flush_me()
                    option = options.ftype.lower()
                    if option == "c":
                        lib.parse_cfile()
                    elif option == "lst":
                        lib.parse_lstfile()
                    else:
                        log.error("Wrong file type! Either c or C or lst or LST, pleeease dont mix caps with small letters, dont have all day for op parsing ;)")
                
                    log.info("Finished Parsing")
                else:
                    log.info("Nothing to parse here, continue.")

        except:
            _type, value, tb = sys.exc_info()
            log.error("Something went wrong when parsing a library: %s" % (sys.exc_info()[1]))
            traceback.print_exception(_type, value, tb, limit=10, file=sys.stdout)
            log.error("If MSSQL, are the access credentials right? Did you set the right permissions on the DB? Did you perform a create_all on mssql or sqlite?")
        
        
    ### OPTION recreate or flush incomplete ###
    
    elif (options.flush or options.createall) and options.updatesigs is None:
        log.error("Options flushall and create-scheme need option --update-sigs or -u !!")
        
        
    ### OPTION recreate, flush or updatesigs ### 
        
    elif options.updatesigs:
        
        try:
            
            if options.flush or options.createall:
                db.flush_all()
                db.create_scheme()
                
            signatures = []
            
            try:
                sigfile = open(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), '..', 'conf', 'signatures.conf'))
                
            except IOError:
                log.error("Something went wrong when reading signature file.")
            else:  
                for line in sigfile:
                    #sanitizing the signatures
                    sig = re.sub('\'','', line.rstrip(),0)
                    signatures.append(sig)
                db.insert_signatures(signatures)
                sigfile.close()
            
            try:
                sigmapping = open(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), '..', 'conf', 'sig_mapping.conf'))
            except IOError:
                log.error("Something went wrong when accessing the sig_mapping.conf.")
            else:
                for line in sigmapping:
                    _map = re.sub('\'','', line.rstrip(),0)
                    arr = re.split('=', _map, 1)
                    db.update_mappings(arr[0], arr[1])
                sigmapping.close()
        
        except:
            log.error("Something went wrong when updating the signatures in DB.")

    ### OPTION printmappings shows all the mappings that exist for sigs in the DB ###
    
    elif options.printmappings is not None:
        info = Diffing.Info.Info(database)
        info.print_mappings()
        
    ### OPTION search_libs gets you the lib IDs to a given libname ###
    
    elif options.libname is not None:
        # sanitizing
        sanilibname = re.sub('\'', '', options.libname, 0)
        info = Diffing.Info.Info(database)
        for item in info.search_libs(sanilibname):
            print("Library ID %s for %s with type %s and OS %s" % (item[0], item[1], item[3], item[2]))
    
    ### OPTION lib_allinfo prints all hit information of one library, given the libid
    
    elif options.lib_allinfo is not None:
        try:
            libid = int(options.lib_allinfo)
        except ValueError:
            log.error("Libid has to be numeric!")
        else:
            print("Libname;Functionname;Sigpattern;Line_Offset")
            for item in Diffing.Info.Info(database).library_info(libid)
                print("%s;%s;%s;%s" % (item[0], item[1], item[2], item[3]))
    
    ### OPTION diff puts out csv content on the commandline or into a pipe, containing hitcounts of a win7 lib compared with a win8 lib ###
    
    elif options.diff:
        
        if None not in (options.lib_one, options.lib_two):
            
            try:
                w7lib = int(options.lib_one)
                w8lib = int(options.lib_two)
            except ValueError:
                log.error("Libids have to be numeric!")
            else:
                print(Diffing.Info.Info(database).diff_twosided(w7lib, w8lib))
                
        else:
            log.error("The Diff Option needs two valid library IDs, get them using the search_libs option, providing a library name!")
        
    ### OPTION diff_byname
    
    elif options.diffbyname is not None:
        sanilibname = re.sub('\'', '', options.diffbyname, 0)
        ids = Diffing.Info.Info(database).search_libs_diffing(sanilibname)
        if ids != -1:
            #info.diff_libs(ids[0],ids[1])   # 0.. Win7, 1.. Win8
            output = info.diff_twosided(ids[0], ids[1])
            print(output)
        else:
            log.error("Something went wrong when choosing libs, maybe more than 2 matches or two libs with the same OS? Or different filetypes? Check with search_libs option!")
    
    else:
        log.error("Wrong Arguments - type -h or --help for Info")
        
if __name__ == '__main__':
    main()
    
