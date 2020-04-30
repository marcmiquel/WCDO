# -*- coding: utf-8 -*-

# script
import wikilanguages_utils
# time
import time
import datetime
from dateutil import relativedelta
import calendar
# system
import os
import sys
import shutil
import re
import random
# databases
import MySQLdb as mdb, MySQLdb.cursors as mdb_cursors
import sqlite3
# files
import gzip
import zipfile
import bz2
import json
import csv
import codecs
import unidecode
# requests and others
import urllib
import webbrowser
import reverse_geocoder as rg
import numpy as np
from random import shuffle
# data
import pandas as pd
# classifier
from sklearn import svm, linear_model
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
# Twice the same table in a short period of time not ok.
# Load all page_titles from all languages is not ok.
import gc



# MAIN
def main():

    languagecode = 'ca'
    (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)

    execution_block_potential_ccc_features()
    execution_block_classifying_ccc()
    execution_block_extract_datasets()


################################################################


def execution_block_potential_ccc_features():

    wikilanguages_utils.send_email_toolaccount('WCDO - CONTENT SELECTION', '# INTRODUCE THE ARTICLE CCC FEATURES')

    # RETRIEVE (POTENTIAL) CCC ARTICLES THAT RELATE TO CCC:
    for languagecode in wikilanguagecodes:
        (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)
        label_potential_ccc_articles_category_crawling(languagecode,page_titles_page_ids,page_titles_qitems)
        del (page_titles_qitems, page_titles_page_ids); gc.collect()


    with ThreadPoolExecutor(max_workers=2) as executor:
        for languagecode in wikilanguagecodes: 
            (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)
            executor.submit(label_potential_ccc_articles_language_weak_wd,languagecode,page_titles_page_ids)
            del (page_titles_qitems, page_titles_page_ids); gc.collect()


    with ThreadPoolExecutor(max_workers=2) as executor:
        for languagecode in wikilanguagecodes: 
            (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)
            executor.submit(label_potential_ccc_articles_has_part_properties_wd,languagecode,page_titles_page_ids)
            executor.submit(label_potential_ccc_articles_affiliation_properties_wd,languagecode,page_titles_qitems)
            del (page_titles_qitems, page_titles_page_ids); gc.collect()

    # RETRIEVE (POTENTIAL) CCC ARTICLES THAT RELATE TO CCC AND ARTICLES THAT RELATE TO OTHER CCC:
    for languagecode in wikilanguagecodes: 
        (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)
        label_potential_ccc_articles_with_links(languagecode,page_titles_page_ids,page_titles_qitems)
        del (page_titles_qitems, page_titles_page_ids); gc.collect()



def execution_block_classifying_ccc():

    wikilanguages_utils.send_email_toolaccount('WCDO - CONTENT SELECTION', '# CLASSIFYING AND CREATING THE DEFINITIVE CCC')
    # Classifying and creating the definitive CCC
    for languagecode in wikilanguagecodes: groundtruth_reaffirmation(languagecode)

    biggest = wikilanguagecodes_by_size[:20]
    smallest = wikilanguagecodes_by_size[20:]

    for languagecode in biggest:
        (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)
        calculate_articles_ccc_binary_classifier(languagecode,'RandomForest',page_titles_page_ids,page_titles_qitems);        

    with ThreadPoolExecutor(max_workers=2) as executor:
        for languagecode in smallest: 
            (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)
            calculate_articles_ccc_binary_classifier(languagecode,'RandomForest',page_titles_page_ids,page_titles_qitems);

    for languagecode in wikilanguagecodes: 
        (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)
        calculate_articles_ccc_main_territory(languagecode)
        calculate_articles_ccc_retrieval_strategies(languagecode)

#    retrieving_ccc_surelist_list()

    create_update_qitems_single_ccc_table()




def execution_block_extract_datasets():

    # EXTRACT CCC DATASETS INTO CSV AND CLEAN OLD DATABASES
    wikilanguages_utils.send_email_toolaccount('WCDO - CONTENT SELECTION', '# EXTRACT CCC DATASETS INTO CSV AND CLEAN OLD DATABASES')
    extract_ccc_tables_to_files()
    extract_ccc_google_schema_json()
    backup_db()

#    wikilanguages_utils.copy_db_for_production(wikipedia_diversity_db, 'content_selection.py', databases_path) # not the right place. it should be in the history or article features.



################################################################

# DIVERSITY FEATURES
####################
# Obtain the Articles contained in the Wikipedia categories with a keyword in title (recursively). This is considered potential CCC.
def label_potential_ccc_articles_category_crawling(languagecode,page_titles_page_ids,page_titles_qitems):

    functionstartTime = time.time()
    function_name = 'label_potential_ccc_articles_category_crawling '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return

    page_ids_page_titles = {v: k for k, v in page_titles_page_ids.items()}

    # CREATING KEYWORDS DICTIONARY
    keywordsdictionary = {}
    if languagecode not in languageswithoutterritory:
        try: qitems=territories.loc[languagecode]['QitemTerritory'].tolist()
        except: qitems=[];qitems.append(territories.loc[languagecode]['QitemTerritory'])
        for qitem in qitems:
            keywords = []
            # territory in Native language
            territorynameNative = territories.loc[territories['QitemTerritory'] == qitem].loc[languagecode]['territorynameNative']
            # demonym in Native language
            try: 
                demonymsNative = territories.loc[territories['QitemTerritory'] == qitem].loc[languagecode]['demonymNative'].split(';')
                # print (demonymsNative)
                for demonym in demonymsNative:
                    if demonym!='':keywords.append(demonym.strip())
            except: pass
            keywords.append(territorynameNative)
            keywordsdictionary[qitem]=keywords

    # language name
    languagenames = languages.loc[languagecode]['nativeLabel'].split(';')
    qitemresult = languages.loc[languagecode]['Qitem']
    keywordsdictionary[qitemresult]=languagenames

    keywords = []
    for values in keywordsdictionary.values():
        for val in values: keywords.append(val.lower())
    print (keywords)

    # STARTING THE CRAWLING
    selectedarticles = {}
    selectedarticles_level = {}

    string = languagecode+' Starting selection of raw CCC.'; 

    print ('With language '+ languagecode +" and Keywords: ")
    print (keywordsdictionary)

    print (keywords)



# PRIMER: s’han d’haver agafat totes les categories. també les que contenen paraules clau.
# https://www.mediawiki.org/wiki/Manual:Category_table

# tot el tema de l'unidecode ja està provat mb keywords.

    dumps_path = '/public/dumps/public/'+languagecode+'wiki/latest/'+languagecode+'wiki-latest-category.sql.gz'
    
    dump_in = gzip.open(dumps_path, 'r')

    print ('Iterating the dump.')
    while True:
        line = dump_in.readline()
        try: line = line.decode("utf-8")
        except UnicodeDecodeError: line = str(line)

        if line == '':
            i+=1
            if i==3: break
        else: i=0

        if wikilanguages_utils.is_insert(line):
#            table_name = wikilanguages_utils.get_table_name(line)
#            columns = wikilanguages_utils.get_columns(line)
            values = wikilanguages_utils.get_values(line)
            if wikilanguages_utils.values_sanity_check(values): rows = wikilanguages_utils.parse_values(values)

            for row in rows:
#                print(row)
                cat_id = int(row[0])
                cat_title = row[1]
                print (cat_title)

                for k in keywords:
                    if unidecode.unidecode(k) in cat_title.replace('_',' ').lower():
                        print (k, cat_title)
                        print ('PREMI!')
                        input('')

# SEGON:
# Category links. Muntar estructura de category links amb diccionaris i sets. Un diccionari amb les relacions entre cat-page i un altre entre cat-cat.
# https://www.mediawiki.org/wiki/Manual:Categorylinks_table










# Obtain the Articles contained in the Wikipedia categories with a keyword in title (recursively). This is considered potential CCC.
def label_potential_ccc_articles_category_crawling_(languagecode,page_titles_page_ids,page_titles_qitems):

    functionstartTime = time.time()
    function_name = 'label_potential_ccc_articles_category_crawling '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return

    page_ids_page_titles = {v: k for k, v in page_titles_page_ids.items()}

    # CREATING KEYWORDS DICTIONARY
    keywordsdictionary = {}
    if languagecode not in languageswithoutterritory:
        try: qitems=territories.loc[languagecode]['QitemTerritory'].tolist()
        except: qitems=[];qitems.append(territories.loc[languagecode]['QitemTerritory'])
        for qitem in qitems:
            keywords = []
            # territory in Native language
            territorynameNative = territories.loc[territories['QitemTerritory'] == qitem].loc[languagecode]['territorynameNative']
            # demonym in Native language
            try: 
                demonymsNative = territories.loc[territories['QitemTerritory'] == qitem].loc[languagecode]['demonymNative'].split(';')
                # print (demonymsNative)
                for demonym in demonymsNative:
                    if demonym!='':keywords.append(demonym.strip())
            except: pass
            keywords.append(territorynameNative)
            keywordsdictionary[qitem]=keywords
    # language name
    languagenames = languages.loc[languagecode]['nativeLabel'].split(';')
    qitemresult = languages.loc[languagecode]['Qitem']
    keywordsdictionary[qitemresult]=languagenames

    # STARTING THE CRAWLING
    selectedarticles = {}
    selectedarticles_level = {}

    string = languagecode+' Starting selection of raw CCC.'; 

    print ('With language '+ languagecode +" and Keywords: ")
    print (keywordsdictionary)

    mysql_con_read = wikilanguages_utils.establish_mysql_connection_read(languagecode); mysql_cur_read = mysql_con_read.cursor()

    # QITEMS
    for item in keywordsdictionary:
        wordlist = keywordsdictionary[item]
#        wordlist = keywordsdictionary['Q1008']
        print ('\n'+(item))
        print (wordlist)

        # GETTING CATEGORIES
        cattitles_total_level = dict()
        cattitles_ids = dict()
        keywordscategories = dict()

        level = 0
        for keyword in wordlist:
            if keyword == '' or keyword == None: continue
            keyword = keyword.replace(' ','%')
#            query = 'SELECT cat_id FROM category INNER JOIN page ON cat_title = page_title WHERE page_namespace = 14 AND CONVERT(cat_title USING utf8mb4) COLLATE utf8mb4_general_ci LIKE '+'"%'+keyword+'%";'#+' ORDER BY cat_id;'

            query = 'SELECT cat_id, cat_title FROM category WHERE CONVERT(cat_title USING utf8mb4) COLLATE utf8mb4_general_ci LIKE'+'"%'+keyword+'%";'#+' ORDER BY cat_id;'

            mysql_cur_read.execute(query)
            # print ("The number of categories for this keyword " + keyword + "is:");
            result = mysql_cur_read.fetchall()
            for row in result:
                cat_id = str(row[0])
                cat_title = str(row[1].decode('utf-8'))

                cattitles_total_level[cat_title] = level
                cattitles_ids[cat_title] = cat_id

                keywordscategories[cat_title] = level

        if len(cattitles_total_level) == 0: continue
        print("The number of categories gathered at level " + str(level) + " is: " + str(len(cattitles_total_level)))

        # CATEGORIES FROM LEVELS
        num_levels = 25
        if languagecode=='en': num_levels = 10
      
        level += 1
        m = 10000

        while (level <= num_levels): # Here we choose the number of levels we prefer.
            newcategories = {}

            if level == 1: curcategories_list = list(keywordscategories.keys())

            if len(curcategories_list) == 0: break
            cur_iteration = curcategories_list[:m]
            del curcategories_list[:m]

            while len(cur_iteration)>0:

#                print(len(cur_iteration))

                # CATEGORIES FROM CATEGORY
                page_asstring = ','.join( ['%s'] * len(cur_iteration) )
                if (len(cur_iteration)!=0):
                    query = 'SELECT page_title FROM page INNER JOIN categorylinks ON page_id=cl_from WHERE page_namespace=14 AND cl_to IN (%s)' % page_asstring                

#                    query = 'SELECT cat_id, cat_title FROM page INNER JOIN categorylinks ON page_id=cl_from INNER JOIN category ON page_title=cat_title WHERE page_namespace=14 AND cl_to IN (%s)' % page_asstring
    #                print (query)
                    mysql_cur_read.execute(query, cur_iteration)
                    result = mysql_cur_read.fetchall()

                    for row in result: #--> PROBLEMES DE ENCODING
                        cat_title = str(row[0].decode('utf-8'))
                        newcategories[cat_title] = None  # this introduces those that are not in for the next iteration.

                for cat_title in cattitles_total_level.keys():
                    try:
                        del newcategories[cat_title]
                    except:
                        pass
                for cat_title in newcategories.keys():
                    cattitles_total_level[cat_title] = level

                cur_iteration = curcategories_list[:m]
                del curcategories_list[:m]

            curcategories_list = list(newcategories.keys())
            if len(curcategories_list) == 0: break

            # get the categories ready for the new iteration
            print("The number of categories gathered at level " + str(level) + " is: " + str(len(newcategories))+ ".\tThe total number of selected categories is now: "+str(len(cattitles_total_level)))
            level = level + 1
     
        cattitles_total_level.update(keywordscategories)
        level = level - 1

        # GETTING ARTICLES FROM LEVELS
        while (level >= 0):

            i = 0
            curcategories_list = []
            for k,v in cattitles_total_level.items():
                if v == level: 
                    curcategories_list.append(k)

            if len(curcategories_list) == 0: 
                level = level - 1
                continue

            cur_iteration = curcategories_list[:m]
            del curcategories_list[:m]
            while len(cur_iteration)>0:
                page_asstring = ','.join( ['%s'] * len(cur_iteration) )
                query = 'SELECT cl_from FROM categorylinks WHERE cl_to IN (%s)' % page_asstring

#                    query = 'SELECT page_id, page_title FROM page INNER JOIN categorylinks ON page_id = cl_from WHERE page_namespace=0 AND page_is_redirect=0 AND cl_to IN (%s)' % page_asstring

#                print (query)
                mysql_cur_read.execute(query, cur_iteration)
                result = mysql_cur_read.fetchall()
                for row in result:
                    i += 1
                    page_id = row[0]

                    try:
                        if selectedarticles_level[page_id]>level: selectedarticles_level[page_id]=level
                    except:
                        selectedarticles_level[page_id]=level

                    if page_id in selectedarticles:
                        selectedarticles[page_id].add(item)
                    else:
                        selectedarticles[page_id] = {item}                        


                cur_iteration = curcategories_list[:m]
                del curcategories_list[:m]


            print("The number of articles gathered at level " + str(level) + " is: " + str(i)+ ". The total number of articles is "+str(len(selectedarticles_level)))
            level = level - 1

    parameters = []

    for page_id, elements in selectedarticles.items():
        
        try: 
            page_title = page_ids_page_titles[page_id]
        except: 
            continue

        try:
            qitem = page_titles_qitems[page_title]
        except:
            qitem=None

        categorycrawling = ";".join(elements)

        parameters.append((categorycrawling,selectedarticles_level[page_id],page_title,page_id,qitem))

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    query = 'UPDATE '+languagecode+'wiki SET (category_crawling_territories,category_crawling_level) = (?,?) WHERE page_title = ? AND page_id = ? AND qitem=?;'
    cursor.executemany(query,parameters)
    conn.commit()

    num_art = wikipedialanguage_numberarticles[languagecode]
    if num_art == 0: percent = 0
    else: percent = 100*len(parameters)/num_art

    # ALL ARTICLES
    wp_number_articles = wikipedialanguage_numberarticles[languagecode]
    string = "The total number of category crawling selected Articles is: " + str(len(parameters)); print (string)
    string = "The total number of Articles in this Wikipedia is: "+str(wp_number_articles)+"\n"; print (string)
    string = "The percentage of category crawling related Articles in this Wikipedia is: "+str(percent)+"\n"; print (string)

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)




# HEY! IT NEEDS EXTENDING FOR THESE OTHER 5 TYPES OF DIVERSITY
def label_potential_lgbt_articles_category_crawling(languagecode,page_titles_page_ids,page_titles_qitems):
    pass
        # 'lgbt_binary integer, '
        # 'category_crawling_lgbt text, '




def label_potential_ccc_articles_with_links(languagecode,page_titles_page_ids,page_titles_qitems):

    functionstartTime = time.time()
    function_name = 'label_potential_ccc_articles_with_links '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return


    # WE NEED TO INCLUDE PAGELINKS TO GENDER (MEN AND WOMEN)
    # WE NEED TO INCLUDE PAGELINKS TO LGBT


        # 'num_outlinks_to_female integer, '
        # 'num_outlinks_to_male integer, '
        # 'num_outlinks_to_lgbt integer, '








    dumps_path = '/public/dumps/public/'+languagecode+'wiki/latest/'+languagecode+'wiki-latest-pagelinks.sql.gz'
#    dumps_path = 'gnwiki-20190720-pagelinks.sql.gz' # read_dump = '/public/dumps/public/wikidatawiki/latest-all.json.gz'
    dump_in = gzip.open(dumps_path, 'r')

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    content_selection_page_title = {}
    content_selection_page_id = {}
    query = 'SELECT page_id, page_title FROM '+languagecode+'wiki WHERE ccc_binary=1;'
    for row in cursor.execute(query):
        content_selection_page_id[row[0]]=row[1]
        content_selection_page_title[row[1]]=row[0]

    other_content_selection_page_title = {}
    other_content_selection_page_id = {}
    query = 'SELECT page_id, page_title FROM '+languagecode+'wiki WHERE ccc_binary=0;'
    for row in cursor.execute(query):
        other_content_selection_page_id[row[0]]=row[1]
        other_content_selection_page_title[row[1]]=row[0]

#    print (len(page_titles_page_ids),len(content_selection_page_id),len(other_content_selection_page_id))
    num_of_outlinks = {}
    num_outlinks_ccc = {}
    num_outlinks_other_ccc = {}

    num_of_inlinks = {}
    num_inlinks_ccc = {}
    num_inlinks_other_ccc = {}

    for page_id in page_titles_page_ids.values():
        num_of_outlinks[page_id]=0
        num_outlinks_ccc[page_id]=0
        num_outlinks_other_ccc[page_id]=0

        num_of_inlinks[page_id]=0
        num_inlinks_ccc[page_id]=0
        num_inlinks_other_ccc[page_id]=0

    print ('Iterating the dump.')
    while True:
        line = dump_in.readline()
        try: line = line.decode("utf-8")
        except UnicodeDecodeError: line = str(line)

        if line == '':
            i+=1
            if i==3: break
        else: i=0

        if wikilanguages_utils.is_insert(line):
            table_name = wikilanguages_utils.get_table_name(line)
            columns = wikilanguages_utils.get_columns(line)
            values = wikilanguages_utils.get_values(line)
            if wikilanguages_utils.values_sanity_check(values): rows = wikilanguages_utils.parse_values(values)

            for row in rows:
#                print(row)
                pl_from = int(row[0])
                pl_from_namespace = row[1]
                pl_title = str(row[2])
                pl_namespace = row[3]

#                if pl_from == 893:
#                    print(row)

                try:
                    pl_title_page_id = page_titles_page_ids[pl_title]
                except:
                    pl_title_page_id = None


                if pl_from_namespace != '0' or pl_namespace != '0': continue

                try:
                    num_of_outlinks[pl_from]= num_of_outlinks[pl_from] + 1
#                    print('num_outlinks')
#                    print (num_of_outlinks[pl_from])
                except:
                    pass

                try:
                    ccc=content_selection_page_id[pl_title_page_id]
                    num_outlinks_ccc[pl_from] = num_outlinks_ccc[pl_from] + 1
                    

#                    print (num_outlinks_ccc[pl_from])
                except:
                    pass

                try:
                    abroad=other_content_selection_page_id[pl_title_page_id]
                    num_outlinks_other_ccc[pl_from] = num_outlinks_other_ccc[pl_from] + 1
#                    print('num_outlinks_other_ccc')
#                    print (num_outlinks_other_ccc[pl_from])
                except:
                    pass


                try:
                    page_id = page_titles_page_ids[pl_title]
                    num_of_inlinks[page_id] = num_of_inlinks[page_id] + 1
#                    print('num_inlinks')                    
#                    print (num_of_inlinks[page_titles_page_ids[pl_title]])
                except:
                    pass

                try:
                    ccc=content_selection_page_id[pl_from]
                    num_inlinks_ccc[pl_title_page_id] = num_inlinks_ccc[pl_title_page_id] + 1
#                    print('num_inlinks_ccc')                    
#                    print (num_inlinks_ccc[page_titles_page_ids[pl_title]])
                except:
                    pass

                try:
                    abroad=other_content_selection_page_id[pl_from]
                    num_inlinks_other_ccc[pl_title_page_id] = num_inlinks_other_ccc[pl_title_page_id] + 1
#                    print('num_inlinks_other_ccc')                    
#                    print (num_inlinks_other_ccc[page_titles_page_ids[pl_title]])
                except:
                    pass

#    input('')
    print ('Done with the dump.')

    n_outlinks=0
    n_outlinks_ccc =0
    n_outlinks_other_ccc =0

    n_inlinks =0
    n_inlinks_ccc =0
    n_inlinks_other_ccc =0

    parameters = []
    for page_title, page_id in page_titles_page_ids.items():
        qitem = page_titles_qitems[page_title]

        num_outlinks = 0
        num_outlinks_to_CCC = 0
        num_outlinks_to_geolocated_abroad = 0
        num_inlinks = 0
        num_inlinks_from_CCC = 0
        num_inlinks_from_geolocated_abroad = 0

        num_outlinks = num_of_outlinks[page_id]
        num_outlinks_to_CCC = num_outlinks_ccc[page_id]
        if num_outlinks!= 0: percent_outlinks_to_CCC = float(num_outlinks_to_CCC)/float(num_outlinks)
        else: percent_outlinks_to_CCC = 0

        num_outlinks_to_geolocated_abroad = num_outlinks_other_ccc[page_id]
        if num_outlinks!= 0: percent_outlinks_to_geolocated_abroad = float(num_outlinks_to_geolocated_abroad)/float(num_outlinks)
        else: percent_outlinks_to_geolocated_abroad = 0

        num_inlinks = num_of_inlinks[page_id]
        num_inlinks_from_CCC = num_inlinks_ccc[page_id]
        if num_inlinks!= 0: percent_inlinks_from_CCC = float(num_inlinks_from_CCC)/float(num_inlinks)
        else: percent_inlinks_from_CCC = 0

        num_inlinks_from_geolocated_abroad = num_inlinks_other_ccc[page_id]
        if num_inlinks!= 0: percent_inlinks_from_geolocated_abroad = float(num_inlinks_from_geolocated_abroad)/float(num_inlinks)
        else: percent_inlinks_from_geolocated_abroad = 0

        parameters.append((num_outlinks,num_outlinks_to_CCC,percent_outlinks_to_CCC,num_outlinks_to_geolocated_abroad,percent_outlinks_to_geolocated_abroad,num_inlinks,num_inlinks_from_CCC,percent_inlinks_from_CCC,num_inlinks_from_geolocated_abroad,percent_inlinks_from_geolocated_abroad,page_id,qitem,page_title))

#        print((num_outlinks,num_outlinks_to_CCC,percent_outlinks_to_CCC,num_outlinks_to_geolocated_abroad,percent_outlinks_to_geolocated_abroad,num_inlinks,num_inlinks_from_CCC,percent_inlinks_from_CCC,num_inlinks_from_geolocated_abroad,percent_inlinks_from_geolocated_abroad,page_id,qitem,page_title))

        if num_outlinks != 0: n_outlinks=n_outlinks+1
        if num_outlinks_to_CCC != 0: n_outlinks_ccc =n_outlinks_ccc+1
        if num_outlinks_to_geolocated_abroad != 0: n_outlinks_other_ccc =n_outlinks_other_ccc+1

        if num_inlinks != 0: n_inlinks =n_inlinks+1
        if num_inlinks_from_CCC != 0: n_inlinks_ccc =n_inlinks_ccc+1
        if num_inlinks_from_geolocated_abroad != 0: n_inlinks_other_ccc =n_inlinks_other_ccc+1

    # print ((n_outlinks,n_outlinks_ccc ,n_outlinks_other_ccc , n_inlinks ,n_inlinks_ccc ,n_inlinks_other_ccc))
    # print ('(n_outlinks,n_outlinks_ccc ,n_outlinks_other_ccc , n_inlinks ,n_inlinks_ccc ,n_inlinks_other_ccc)')
    
    query = 'UPDATE '+languagecode+'wiki SET (num_outlinks,num_outlinks_to_CCC,percent_outlinks_to_CCC,num_outlinks_to_geolocated_abroad,percent_outlinks_to_geolocated_abroad,num_inlinks,num_inlinks_from_CCC,percent_inlinks_from_CCC,num_inlinks_from_geolocated_abroad,percent_inlinks_from_geolocated_abroad)=(?,?,?,?,?,?,?,?,?,?) WHERE page_id = ? AND qitem = ? AND page_title=?;'
        
    cursor.executemany(query,parameters)
    conn.commit()

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)
    print(duration)



# Obtain the Articles with a "weak" language property that is associated the language. This is considered potential CCC.
def label_potential_ccc_articles_language_weak_wd(languagecode,page_titles_page_ids):

    functionstartTime = time.time()
    function_name = 'label_potential_ccc_articles_language_weak_wd '+languagecode
#    if create_function_account_db(function_name, 'check','')==1: return

    conn = sqlite3.connect(databases_path + wikidata_db); cursor = conn.cursor()

    # language qitems
    qitemresult = languages.loc[languagecode]['Qitem']
    if ';' in qitemresult: qitemresult = qitemresult.split(';')
    else: qitemresult = [qitemresult];

    # get Articles
    qitem_properties = {}
    qitem_page_titles = {}
    other_ccc_language = {}
    query = 'SELECT language_weak_properties.qitem, language_weak_properties.property, language_weak_properties.qitem2, sitelinks.page_title FROM language_weak_properties INNER JOIN sitelinks ON sitelinks.qitem = language_weak_properties.qitem WHERE sitelinks.langcode ="'+languagecode+'wiki"'
    for row in cursor.execute(query):
        qitem = row[0]
        wdproperty = row[1]
        qitem2 = row[2]
        page_title = row[3].replace(' ','_')

        if qitem2 not in qitemresult: 
            if qitem not in other_ccc_language: other_ccc_language[qitem]=1
            else: other_ccc_language[qitem]=other_ccc_language[qitem]+1

        else:
    #        print ((qitem, wdproperty, language_properties_weak[wdproperty], page_title))
            # Put the items into a dictionary
            value = wdproperty+':'+qitem2
            if qitem not in qitem_properties: qitem_properties[qitem]=value
            else: qitem_properties[qitem]=qitem_properties[qitem]+';'+value

        qitem_page_titles[qitem]=page_title


    # Get the tuple ready to insert.
    ccc_language_items = []
    for qitem, values in qitem_properties.items():
        try: 
            page_id=page_titles_page_ids[qitem_page_titles[qitem]]
            ccc_language_items.append((values,qitem_page_titles[qitem],qitem,page_id))
        except: continue

    # Get the tuple ready to insert for other language strong CCC.
    other_ccc_language_items = []
    for qitem, values in other_ccc_language.items():
        try: 
            page_id=page_titles_page_ids[qitem_page_titles[qitem]]
            other_ccc_language_items.append((str(values),qitem_page_titles[qitem],qitem,page_id))
        except: 
            pass


    # Insert to the corresponding CCC database.
    conn2 = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor2 = conn2.cursor()
    query = 'UPDATE '+languagecode+'wiki SET language_weak_wd = ? WHERE page_title = ? AND qitem = ? AND page_id = ?;'
    cursor2.executemany(query,ccc_language_items)
    conn2.commit()


   # Insert to the corresponding CCC database.
    query = 'UPDATE '+languagecode+'wiki SET other_ccc_language_weak_wd = ? WHERE page_title = ? AND qitem = ? AND page_id = ?;'
    cursor2.executemany(query,other_ccc_language_items)
    conn2.commit()

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)




# Get the Articles with the number of affiliation-like properties to other Articles already retrieved as CCC.
def label_potential_ccc_articles_affiliation_properties_wd(languagecode,page_titles_page_ids):

    functionstartTime = time.time()

    function_name = 'label_potential_ccc_articles_affiliation_properties_wd '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return


    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    conn2 = sqlite3.connect(databases_path + wikidata_db); cursor2 = conn2.cursor()

    ccc_articles={}
    for row in cursor.execute('SELECT page_title, qitem FROM '+languagecode+'wiki WHERE ccc_binary=1;'):
        ccc_articles[row[1]]=row[0].replace(' ','_')

    potential_ccc_articles={}
    for row in cursor.execute('SELECT page_title, qitem FROM '+languagecode+'wiki;'):
        potential_ccc_articles[row[1]]=row[0].replace(' ','_')

#    print (affiliation_properties)
#    input('')

    
    other_ccc_affiliation_qitems = {}
    qitem_page_titles = {}
    selected_qitems = {}
    query = 'SELECT affiliation_properties.qitem, affiliation_properties.property, affiliation_properties.qitem2, sitelinks.page_title FROM affiliation_properties INNER JOIN sitelinks ON sitelinks.qitem = affiliation_properties.qitem WHERE sitelinks.langcode ="'+languagecode+'wiki"'
    for row in cursor2.execute(query):
        qitem = row[0]
        wdproperty = row[1]
        qitem2 = row[2]
        page_title = row[3].replace(' ','_')

        if (qitem2 in ccc_articles):
#            if (qitem in ccc_articles): continue
#                print ((qitem, page_title, wdproperty, affiliation_properties[wdproperty],ccc_articles[qitem2],'ALREADY IN!'))           
#            elif (qitem in potential_ccc_articles): continue
#                print ((qitem, page_title, wdproperty, affiliation_properties[wdproperty],ccc_articles[qitem2],'POTENTIAL.'))
#            else:
#                print ((qitem, page_title, wdproperty, affiliation_properties[wdproperty],ccc_articles[qitem2],'NEW NEW NEW NEW NEW!'))
            if qitem not in selected_qitems:
                selected_qitems[qitem]=[page_title,wdproperty,qitem2]
            else:
                selected_qitems[qitem]=selected_qitems[qitem]+[wdproperty,qitem2]
#    print (len(selected_qitems))
#    for keys,values in selected_qitems.items(): print (keys,values)


        else:
            if qitem not in other_ccc_affiliation_qitems: other_ccc_affiliation_qitems[qitem]=1
            else: other_ccc_affiliation_qitems[qitem]=other_ccc_affiliation_qitems[qitem]+1

        qitem_page_titles[qitem]=page_title


    ccc_affiliation_items = []
    for qitem, values in selected_qitems.items():
        page_title=values[0]
        try: page_id=page_titles_page_ids[page_title]
        except: continue
        value = ''
        for x in range(0,int((len(values)-1)/2)):
            if x >= 1: value = value + ';'
            value = value + values[x*2+1]+':'+values[x*2+2]
#        print ((value,page_title,qitem,page_id))
        ccc_affiliation_items.append((value,page_title,qitem,page_id))
#    print (len(ccc_affiliation_items))


    other_ccc_affiliation_items = []
    for qitem, values in other_ccc_affiliation_qitems.items():
        try: 
            page_id=page_titles_page_ids[qitem_page_titles[qitem]]
            other_ccc_affiliation_items.append((str(values),qitem_page_titles[qitem],qitem,page_id))
        except: 
            pass


    # INSERT INTO CCC DATABASE
    query = 'UPDATE '+languagecode+'wiki SET affiliation_wd = ? WHERE page_title = ? AND qitem = ? AND page_id = ?;'
    cursor.executemany(query,ccc_affiliation_items)
    conn.commit()

    query = 'UPDATE '+languagecode+'wiki SET other_ccc_affiliation_wd = ? WHERE page_title = ? AND qitem = ? AND page_id = ?;'
    cursor.executemany(query,other_ccc_affiliation_items)
    conn.commit()

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)



# Get the Articles with the properties that state that has Articles already retrieved as CCC as part of them.
def label_potential_ccc_articles_has_part_properties_wd(languagecode,page_titles_page_ids):

    functionstartTime = time.time()

    function_name = 'label_potential_ccc_articles_has_part_properties_wd '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    conn2 = sqlite3.connect(databases_path + wikidata_db); cursor2 = conn2.cursor()

    ccc_articles={}
    for row in cursor.execute('SELECT page_title, qitem FROM '+languagecode+'wiki WHERE ccc_binary=1;'):
        ccc_articles[row[1]]=row[0].replace(' ','_')

    potential_ccc_articles={}
    for row in cursor.execute('SELECT page_title, qitem FROM '+languagecode+'wiki;'):
        potential_ccc_articles[row[1]]=row[0].replace(' ','_')


    qitem_page_titles = {}
    other_ccc_has_part_properties = {}
    selected_qitems={}
    query = 'SELECT has_part_properties.qitem, has_part_properties.property, has_part_properties.qitem2, sitelinks.page_title FROM has_part_properties INNER JOIN sitelinks ON sitelinks.qitem = has_part_properties.qitem WHERE sitelinks.langcode ="'+languagecode+'wiki"'
    for row in cursor2.execute(query):
        qitem = row[0]
        wdproperty = row[1]
        qitem2 = row[2]
        page_title = row[3].replace(' ','_')

        if (qitem2 in ccc_articles) and (qitem in potential_ccc_articles):
            # print ((qitem, page_title, wdproperty, has_part_properties[wdproperty],ccc_articles[qitem2]))
            if qitem not in selected_qitems:
                selected_qitems[qitem]=[page_title,wdproperty,qitem2]
            else:
                selected_qitems[qitem]=selected_qitems[qitem]+[wdproperty,qitem2]


        if (qitem2 not in ccc_articles) and (qitem not in potential_ccc_articles) and (qitem not in ccc_articles):

            if qitem not in other_ccc_has_part_properties:
                other_ccc_has_part_properties[qitem] =

            if qitem2 not in other_ccc_has_part_properties: other_ccc_has_part_properties[qitem]=1
            else: other_ccc_has_part_properties[qitem]=other_ccc_has_part_properties[qitem]+1

        qitem_page_titles[qitem] = page_title

#    for keys,values in selected_qitems.items(): print (keys,values)
#    input('')

    ccc_has_part_items = []
    for qitem, values in selected_qitems.items():
        page_title=values[0]
        try: page_id=page_titles_page_ids[page_title]
        except: continue
        value = ''
#        print (values)
        for x in range(0,int((len(values)-1)/2)):
            if x >= 1: value = value + ';'
            value = value + values[x*2+1]+':'+values[x*2+2]
#        print ((value,page_title,qitem,page_id))
        ccc_has_part_items.append((value,page_title,qitem,page_id))

    other_ccc_has_part_items = []
    for qitem, values in other_ccc_has_part_properties.items():
        try: 
            page_id=page_titles_page_ids[qitem_page_titles[qitem]]
            other_ccc_has_part_items.append((str(values),qitem_page_titles[qitem],qitem,page_id))
        except: 
            pass


    # INSERT INTO CCC DATABASE
    query = 'UPDATE '+languagecode+'wiki SET has_part_wd = ? WHERE page_title = ? AND qitem = ? AND page_id = ?;'
    cursor.executemany(query,ccc_has_part_items)
    conn.commit()

    query = 'UPDATE '+languagecode+'wiki SET other_ccc_has_part_wd = ? WHERE page_title = ? AND qitem = ? AND page_id = ?;'
    cursor.executemany(query,other_ccc_has_part_items)
    conn.commit()

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)



def label_time_interval_wd():


    query = 'SELECT qitem, property, qitem2 FROM instance_of_subclasses_of_properties WHERE qitem2 IN ("","")';



# obtains the blacklisted/whitelist articles from the previous CCC, stores them in the new database and uses them to assign them ccc_binary = 0.
def retrieving_ccc_surelist_list():

    function_name = 'retrieving_ccc_surelist_list '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return

    functionstartTime = time.time()

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS ccc_surelist (languagecode text, qitem text, ccc_binary int, PRIMARY KEY (languagecode, qitem));")

    conn2 = sqlite3.connect(databases_path + 'ccc_old.db'); cursor2 = conn2.cursor()
    query = 'SELECT languagecode, qitem FROM ccc_surelist WHERE page_namespace=0;'

    (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)

    lang_articles = {}
    for languagecode in wikilanguagecodes:
        lang_articles[languagecode]=[]

    qitem = ''
    parameters = []
    for row in cursor.execute(query):
        languagecode = row[0]
        if languagecode != old_languagecode and qitem!='':
            (page_titles_qitems, page_titles_page_ids)=wikilanguages_utils.load_dicts_page_ids_qitems(0,languagecode)
            qitems_page_titles = {v: k for k, v in page_titles_qitems.items()}

        qitem = row[1]
        ccc_binary = row[2]
        page_id = page_titles_page_ids[qitems_page_titles[qitem]]

        parameters.append((languagecode,qitem,ccc_binary))
        lang_articles[languagecode]=lang_articles[languagecode].append((ccc_binary,page_id,qitem))

        old_languagecode = languagecode

    query = "INSERT INTO ccc_surelist (languagecode, qitem, ccc_binary) VALUES (?,?,?);"
    cursor.executemany(query,parameters)
    conn.commit()

    for languagecode in wikilanguagecodes:
        query = 'UPDATE '+languagecode+'wiki SET ccc_binary=? WHERE page_id = ? AND qitem = ?;'
        cursor.executemany(query,lang_articles[languagecode])
        conn.commit()

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)




### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- 

# ARTICLE CCC CLASSIFYING / SCORING FUNCTIONS
#############################################

def get_ccc_training_data(languagecode):

    # OBTAIN THE DATA TO FIT.
    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    query = 'SELECT * FROM '+languagecode+'wiki WHERE ccc_binary IS NOT NULL;'
    ccc_df = pd.read_sql_query(query, conn)


    positive_features = ['category_crawling_territories','category_crawling_level','language_weak_wd','affiliation_wd','has_part_wd','num_inlinks_from_CCC','num_outlinks_to_CCC','percent_inlinks_from_CCC','percent_outlinks_to_CCC','ccc_binary']

    negative_features = ['other_ccc_language_strong_wd','other_ccc_created_by_wd','other_ccc_part_of_wd','other_ccc_language_weak_wd','other_ccc_affiliation_wd','other_ccc_has_part_wd']  #'other_ccc_country_wd','other_ccc_location_wd' are out because now are considered totally negative groundtruth (25.9.18)

#    negative_features_2 = ['other_ccc_keyword_title','other_ccc_category_crawling_relative_level', 'num_inlinks_from_geolocated_abroad', 'num_outlinks_to_geolocated_abroad', 'percent_inlinks_from_geolocated_abroad', 'percent_outlinks_to_geolocated_abroad']

    features = ['qitem']+positive_features+negative_features
#    features = positive_features

    ccc_df = ccc_df[features]
    ccc_df = ccc_df.set_index(['qitem'])
#    print (ccc_df.head())
    if len(ccc_df.index.tolist())==0: print ('It is not possible to classify Wikipedia Articles as there is no groundtruth.'); return (0,0,[],[]) # maxlevel,num_articles_ccc,ccc_df_list,binary_list
    ccc_df = ccc_df.fillna(0)


    # FORMAT THE DATA FEATURES AS NUMERICAL FOR THE MACHINE LEARNING
    category_crawling_paths=ccc_df['category_crawling_territories'].tolist()
    for n, i in enumerate(category_crawling_paths):
        if i is not 0:
            category_crawling_paths[n]=1
            if i.count(';')>=1: category_crawling_paths[n]=i.count(';')+1
        else: category_crawling_paths[n]=0
    ccc_df = ccc_df.assign(category_crawling_territories = category_crawling_paths)

    category_crawling_level=ccc_df['category_crawling_level'].tolist()
    maxlevel = max(category_crawling_level)
    for n, i in enumerate(category_crawling_level):
        if i > 0:
            category_crawling_level[n]=abs(i-(maxlevel+1))
        else:
            category_crawling_level[n]=0
    ccc_df = ccc_df.assign(category_crawling_level = category_crawling_level)

    language_weak_wd=ccc_df['language_weak_wd'].tolist()
    for n, i in enumerate(language_weak_wd):
        if i is not 0: language_weak_wd[n]=1
        else: language_weak_wd[n]=0
    ccc_df = ccc_df.assign(language_weak_wd = language_weak_wd)

    affiliation_wd=ccc_df['affiliation_wd'].tolist()
    for n, i in enumerate(affiliation_wd):
        if i is not 0: 
            affiliation_wd[n]=1
            if i.count(';')>=1: affiliation_wd[n]=i.count(';')+1
        else: affiliation_wd[n]=0
    ccc_df = ccc_df.assign(affiliation_wd = affiliation_wd)

    has_part_wd=ccc_df['has_part_wd'].tolist()
    for n, i in enumerate(has_part_wd):
        if i is not 0: 
            has_part_wd[n]=1
            if i.count(';')>=1: has_part_wd[n]=i.count(';')+1
        else: has_part_wd[n]=0
    ccc_df = ccc_df.assign(has_part_wd = has_part_wd)
#    print (ccc_df.head())

    
    # SAMPLING
    sampling_method = 'negative_sampling'
    print ('sampling method: '+sampling_method)

    if sampling_method == 'negative_sampling':
        ccc_df_yes = ccc_df.loc[ccc_df['ccc_binary'] == 1]
        ccc_df_yes = ccc_df_yes.drop(columns=['ccc_binary'])
        ccc_df_list_yes = ccc_df_yes.values.tolist()
        num_articles_ccc = len(ccc_df_list_yes)

        ccc_df_list_probably_no = []
        size_sample = 6
        if languagecode == 'en': size_sample = 4 # exception for English
        for i in range(1,1+size_sample):
            ccc_df = ccc_df.sample(frac=1) # randomize the rows order
            ccc_df_probably_no = ccc_df.loc[ccc_df['ccc_binary'] != 1]
            ccc_df_probably_no = ccc_df_probably_no.drop(columns=['ccc_binary'])
            ccc_df_list_probably_no = ccc_df_list_probably_no + ccc_df_probably_no.values.tolist()[:num_articles_ccc]

        num_probably_no = len(ccc_df_list_probably_no)
        ccc_df_list = ccc_df_list_yes + ccc_df_list_probably_no
        binary_list = [1]*num_articles_ccc+[0]*num_probably_no

    if sampling_method == 'balanced_sampling':
        ccc_df = ccc_df.sample(frac=1) # randomize the rows order
        ccc_df_yes = ccc_df.loc[ccc_df['ccc_binary'] == 1]
        ccc_df_yes = ccc_df_yes.drop(columns=['ccc_binary'])
    #    print (ccc_df_yes.head())

        ccc_df_no = ccc_df.loc[ccc_df['ccc_binary'] == 0]
        ccc_df_no = ccc_df_no.drop(columns=['ccc_binary'])
    #    print (ccc_df_no.head())

        sample = 10000 # the number samples per class
        sample = min(sample,len(ccc_df_yes),len(ccc_df_no))
        ccc_df_list_yes = ccc_df_yes.values.tolist()[:sample]
        ccc_df_list_no = ccc_df_no.values.tolist()[:sample]

        ccc_df_list = ccc_df_list_yes+ccc_df_list_no
        binary_list = [1]*sample+[0]*sample
        num_articles_ccc = len(ccc_df_yes)

    print ('\nConverting the dataframe...')
    print ('These are its columns:')
    print (list(ccc_df_yes.columns.values))

#    print (maxlevel)
#    print (len(num_articles_ccc))
#    print (len(ccc_df_list))
#    print (len(binary_list))

    return maxlevel,num_articles_ccc,ccc_df_list,binary_list


def get_ccc_testing_data(languagecode,maxlevel):

    # OBTAIN THE DATA TO TEST
    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
#    query = 'SELECT * FROM '+languagecode+'wiki WHERE ccc_binary IS NULL;' # ALL
    
    # WE GET THE POTENTIAL CCC ARTICLES THAT HAVE NOT BEEN 1 BY ANY OTHER MEANS.
    # For the testing takes those with one of these features not null (category crawling, language weak, affiliation or has part).
    query = 'SELECT * FROM '+languagecode+'wiki WHERE ccc_binary IS NULL AND (category_crawling_territories IS NOT NULL OR category_crawling_level IS NOT NULL OR language_weak_wd IS NOT NULL OR affiliation_wd IS NOT NULL OR has_part_wd IS NOT NULL);'

    # For the testing takes those with one of these features not null (category crawling, language weak, affiliation or has part), and those with keywords on title.
#    query = 'SELECT * FROM '+languagecode+'wiki WHERE ccc_binary IS NULL AND (category_crawling_territories IS NOT NULL OR category_crawling_level IS NOT NULL OR language_weak_wd IS NOT NULL OR affiliation_wd IS NOT NULL OR has_part_wd IS NOT NULL) OR keyword_title IS NOT NULL;' # POTENTIAL

    potential_ccc_df = pd.read_sql_query(query, conn)

    positive_features = ['category_crawling_territories','category_crawling_level','language_weak_wd','affiliation_wd','has_part_wd','num_inlinks_from_CCC','num_outlinks_to_CCC','percent_inlinks_from_CCC','percent_outlinks_to_CCC']

    negative_features = ['other_ccc_language_strong_wd','other_ccc_created_by_wd','other_ccc_part_of_wd','other_ccc_language_weak_wd','other_ccc_affiliation_wd','other_ccc_has_part_wd']

#    negative_features_2 = ['other_ccc_keyword_title','other_ccc_category_crawling_relative_level', 'num_inlinks_from_geolocated_abroad', 'num_outlinks_to_geolocated_abroad', 'percent_inlinks_from_geolocated_abroad', 'percent_outlinks_to_geolocated_abroad']
    features = ['page_title'] + positive_features + negative_features
#    features = positive_features

    potential_ccc_df = potential_ccc_df[features]
    potential_ccc_df = potential_ccc_df.set_index(['page_title'])
    potential_ccc_df = potential_ccc_df.fillna(0)

    # FORMAT THE DATA FEATURES AS NUMERICAL FOR THE MACHINE LEARNING
    category_crawling_paths=potential_ccc_df['category_crawling_territories'].tolist()
    for n, i in enumerate(category_crawling_paths):
        if i is not 0:
            category_crawling_paths[n]=1
            if i.count(';')>=1: category_crawling_paths[n]=i.count(';')+1
        else: category_crawling_paths[n]=0
    potential_ccc_df = potential_ccc_df.assign(category_crawling_territories = category_crawling_paths)

    category_crawling_level=potential_ccc_df['category_crawling_level'].tolist()
#    print (maxlevel)
#    print (max(category_crawling_level))
    for n, i in enumerate(category_crawling_level):
        if i > 0:
            category_crawling_level[n]=abs(i-(maxlevel+1))
        else:
            category_crawling_level[n]=0
    potential_ccc_df = potential_ccc_df.assign(category_crawling_level = category_crawling_level)

    language_weak_wd=potential_ccc_df['language_weak_wd'].tolist()
    for n, i in enumerate(language_weak_wd):
        if i is not 0:
            language_weak_wd[n]=1
        else: language_weak_wd[n]=0
    potential_ccc_df = potential_ccc_df.assign(language_weak_wd = language_weak_wd)

    affiliation_wd=potential_ccc_df['affiliation_wd'].tolist()
    for n, i in enumerate(affiliation_wd):
        if i is not 0:
            affiliation_wd[n]=1
            if i.count(';')>=1: affiliation_wd[n]=i.count(';')+1
        else: affiliation_wd[n]=0
    potential_ccc_df = potential_ccc_df.assign(affiliation_wd = affiliation_wd)

    has_part_wd=potential_ccc_df['has_part_wd'].tolist()
    for n, i in enumerate(has_part_wd):
        if i is not 0:
            has_part_wd[n]=1
            if i.count(';')>=1: has_part_wd[n]=i.count(';')+1
        else: has_part_wd[n]=0
    potential_ccc_df = potential_ccc_df.assign(has_part_wd = has_part_wd)


    # NOT ENOUGH ARTICLES
    if len(potential_ccc_df)==0: print ('There are not potential CCC Articles, so it returns empty'); return
    potential_ccc_df = potential_ccc_df.sample(frac=1) # randomize the rows order

    print ('We selected this number of potential CCC Articles: '+str(len(potential_ccc_df)))

    return potential_ccc_df


### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- ### --- 

# Takes the ccc_score and decides whether it must be in ccc or not.
def calculate_articles_ccc_binary_classifier(languagecode,classifier,page_titles_page_ids,page_titles_qitems):

    function_name = 'calculate_articles_ccc_binary_classifier '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return

    functionstartTime = time.time()
    print ('\nObtaining the final CCC for language: '+languagecode)

    # FIT THE SVM MODEL
    maxlevel,num_articles_ccc,ccc_df_list,binary_list = get_ccc_training_data(languagecode)
    print ('Fitting the data into the classifier.')
    print ('The data has '+str(len(ccc_df_list))+' samples.')
    if num_articles_ccc == 0 or len(ccc_df_list)<10: print ('There are not enough samples.'); return

    X = ccc_df_list
    y = binary_list
#    print (X)
#    print (y)

    print ('The chosen classifier is: '+classifier)
    if classifier=='SVM':
        clf = svm.SVC()
        clf.fit(X, y)
    if classifier=='RandomForest':
        clf = RandomForestClassifier(n_estimators=100)
        clf.fit(X, y)
    if classifier=='LogisticRegression':
        clf = linear_model.LogisticRegression(solver='liblinear')
        clf.fit(X, y)
    if classifier=='GradientBoosting':
        clf = GradientBoostingClassifier()
        clf.fit(X, y)

    print ('The fit classes are: '+str(clf.classes_))
    print ('The fit has a score of: '+str(clf.score(X, y, sample_weight=None)))
    print (clf.feature_importances_.tolist())
#    input('')

    # TEST THE DATA
    print ('Calculating which page is IN or OUT...')
    potential_ccc_df = get_ccc_testing_data(languagecode,maxlevel)



    if potential_ccc_df is None: 
        print ('No Articles to verify.'); 
        duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
        create_function_account_db(function_name, 'mark', duration)
        return     
    if len(potential_ccc_df)==0: 
        print ('No Articles to verify.'); 
        duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
        create_function_account_db(function_name, 'mark', duration)
        return

    page_titles = potential_ccc_df.index.tolist()
    potential = potential_ccc_df.values.tolist()

    print ('We print the results (0 for no, 1 for yes):')
    visible = 0
    print (visible)

    selected=[]

    # DO NOT PRINT THE CLASSIFIER RESULTS ARTICLE BY ARTICLE
    if visible == 0:
    #    testdict = {}
        result = clf.predict(potential)
        i = 0
        for x in result:
    #        testdict[page_titles[i]]=(x,potential[i])
            if x == 1:
                page_title=page_titles[i]
                selected.append((page_titles_page_ids[page_title],page_titles_qitems[page_title]))
            i += 1
#    print (testdict)

    # PRINT THE CLASSIFIER RESULTS ARTICLE BY ARTICLE
    else:
        # provisional
#        print (potential[:15])
#        print (page_titles[:15])
        count_yes=0
        count_no=0
        for n,i in enumerate(potential):
            result = clf.predict([i])
            page_title=page_titles[n]
            if result[0] == 1:
                count_yes+=1
                print (['category_crawling_paths','category_crawling_level','language_weak_wd','affiliation_wd','has_part_wd','num_inlinks_from_CCC','num_outlinks_to_CCC','percent_inlinks_from_CCC','percent_outlinks_to_CCC','other_ccc_language_strong_wd','other_ccc_created_by_wd','other_ccc_part_of_wd','other_ccc_language_weak_wd','other_ccc_affiliation_wd','other_ccc_has_part_wd'])
                print(i)
                print(clf.predict_proba([i]).tolist())
                print (str(count_yes)+'\tIN\t'+page_title+'.\n')

                try: selected.append((page_titles_page_ids[page_title],page_titles_qitems[page_title]))
                except: pass
            else:
                count_no+=1
                print (['category_crawling_paths','category_crawling_level','language_weak_wd','affiliation_wd','has_part_wd','num_inlinks_from_CCC','num_outlinks_to_CCC','percent_inlinks_from_CCC','percent_outlinks_to_CCC','other_ccc_language_strong_wd','other_ccc_created_by_wd','other_ccc_part_of_wd','other_ccc_language_weak_wd','other_ccc_affiliation_wd','other_ccc_has_part_wd'])
                print(i)
                print(clf.predict_proba([i]).tolist())
                print (str(count_no)+'\tOUT:\t'+page_title+'.\n')
#                input('')

    num_art = wikipedialanguage_numberarticles[languagecode]
    if num_art == 0: 
        percent = 0
        percent_selected = '0'
    else: 
        percent = round(100*num_articles_ccc/num_art,3)
        percent_selected = str(round(100*(num_articles_ccc+len(selected))/num_art,3))


    print ('\nThis Wikipedia ('+languagecode+'wiki) has a total of '+str(wikipedialanguage_numberarticles[languagecode])+' Articles.')
    print ('There were already '+str(num_articles_ccc)+' CCC Articles selected as groundtruth. This is a: '+str(percent)+'% of the WP language edition.')

    print ('\nThis algorithm CLASSIFIED '+str(len(selected))+' Articles as ccc_binary = 1 from a total of '+str(len(potential))+' from the testing data. This is a: '+str(round(100*len(selected)/len(potential),3))+'%.')
    print ('With '+str(num_articles_ccc+len(selected))+' Articles, the current and updated percentage of CCC is: '+percent_selected+'% of the WP language edition.\n')

#    evaluate_content_selection_manual_assessment(languagecode,selected,page_titles_page_ids)
#    input('')

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 1 WHERE page_id = ? AND qitem = ?;'
    cursor.executemany(query,selected)
    conn.commit()

    print ('Language CCC '+(languagecode)+' created.')

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)



def calculate_articles_lgbt_binary_classifier():
    # using category_crawling_lgbt, outlinks_to_lgbt, inlinks_from_lgbt,....

    pass





def calculate_articles_ccc_main_territory(languagecode):

    functionstartTime = time.time()
    function_name = 'calculate_articles_ccc_main_territory '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return

    if languagecode in languageswithoutterritory: print ('This language has no territories: '+languagecode); return

    number_iterations = 3
    print ('number of iterations: '+str(number_iterations))
    for i in range(1,number_iterations+1):
        print ('* iteration nº: '+str(i))
        # this function verifies the keywords associated territories, category crawling associated territories, and the wikidata associated territories in order to choose one.
        conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()

        if languagecode not in languageswithoutterritory:
            try: qitems=territories.loc[languagecode]['QitemTerritory'].tolist()
            except: qitems=[];qitems.append(territories.loc[languagecode]['QitemTerritory'])

        main_territory_list = []
        main_territory_in = {}
        query = 'SELECT qitem, main_territory FROM '+languagecode+'wiki WHERE main_territory IS NOT NULL';
        for row in cursor.execute(query):
            main_territory_in[row[0]]=row[1]
    #    print (len(main_territory_in))

        query = 'SELECT qitem, page_id, main_territory, country_wd, location_wd, part_of_wd, has_part_wd, keyword_title, category_crawling_territories, created_by_wd, affiliation_wd FROM '+languagecode+'wiki'+' WHERE main_territory IS NULL AND ccc_binary=1'
#        print (query)
        for row in cursor.execute(query):
#            print (row)

            qitem = str(row[0])
            page_id = row[1]
            main_territory = row[2]
    #        print ('* row:')
    #        print (row)
            
            # check the rest of parameters to assign the main territory.
            main_territory_dict={}

            for x in range(3,len(row)):
                parts = row[x]
    #            print (x)

                if parts != None:
                    if ';' in parts:
                        parts = row[x].split(';')

                        if x==7: # exception: it is in keywords and there is only one Qitem that is not language. IN.
                            in_part=[]
                            for part in parts:
                                if part in qitems: in_part.append(part)
                            if len(in_part) >0:
                                if in_part[0] in qitems:
                                    main_territory_list.append((main_territory, qitem, page_id))
                                    main_territory_in[qitem]=main_territory
#                                    print ('number 7.1')
#                                    print ((main_territory, qitem, page_id))
                                    continue

                        for part in parts:
                            if ':' in part:
                                subparts = part.split(':')

                                if len(subparts) == 3:
                                    subpart = subparts[2]

                                if len(subparts) == 2: # we are giving it the main territory of the subpart. this is valid for: part_of_wd, has_part_wd, created_by_wd, affiliation_wd.
                                    subpart = subparts[1]
                                    try:
    #                                        print ('número 2 this: '+subpart+' is: '+ main_territory_in[subpart])
                                        subpart = main_territory_in[subpart]
                                    except: pass

                                if subpart in qitems:
                                    if subpart not in main_territory_dict:
                                        main_territory_dict[subpart]=1
                                    else:
                                        main_territory_dict[subpart]=main_territory_dict[subpart]+1
                            else:
    #                                print ('número 1 per part.')
                                if part in qitems:
                                    if part not in main_territory_dict:
                                        main_territory_dict[part]=1
                                    else:
                                        main_territory_dict[part]=main_territory_dict[part]+1
                    else:
    #                        print ('un de sol.')

                        if ':' in parts:
                            subparts = parts.split(':')

                            if len(subparts) == 3:
                                subpart = subparts[2]

                            if len(subparts) == 2: # we are giving it the main territory of the subpart. this is valid for: part_of_wd, has_part_wd, created_by_wd, affiliation_wd.
                                subpart = subparts[1]
                                try:
    #                                    print ('número 2 this: '+subpart+' is: '+ main_territory_in[subpart])
                                    subpart = main_territory_in[subpart]
                                except: pass

                            if subpart in qitems:
                                if subpart not in main_territory_dict:
                                    main_territory_dict[subpart]=1
                                else:
                                    main_territory_dict[subpart]=main_territory_dict[subpart]+1

                        else:
                            # exception: it is in keywords and there is only one Qitem. IN.

                            if parts in qitems:
                                if x == 7:
                                    main_territory_list.append((main_territory, qitem, page_id))
                                    main_territory_in[qitem]=main_territory
#                                    print ('number 7.2')
#                                    print ((main_territory, qitem, page_id))
                                    continue     

                                if parts not in main_territory_dict:
                                    main_territory_dict[parts]=1
                                else:
                                    main_territory_dict[parts]=main_territory_dict[parts]+1
                else:
    #                    print ('None')
                    pass

    #        print ('here is the selection:')
    #        print (main_territory_dict)

            # choose the territory with more occurences
            if len(main_territory_dict)>1: 
                if sorted(main_territory_dict.items(), key=lambda item: (item[1], item[0]), reverse=True)[0][1] == sorted(main_territory_dict.items(), key=lambda item: (item[1], item[0]), reverse=True)[1][1]:
                    main_territory=None
    #                    print ('NO EN TENIM.')
                    continue
                else:
                    main_territory=sorted(main_territory_dict.items(), key=lambda item: (item[1], item[0]), reverse=True)[0][0] 
            elif len(main_territory_dict)>0:
                main_territory=list(main_territory_dict.keys())[0]

            # put it into a list
            main_territory_list.append((main_territory, qitem, page_id))
#            print ('this is in:')
#            print ((main_territory, qitem, page_id))

        query = 'UPDATE '+languagecode+'wiki SET main_territory = ? WHERE qitem = ? AND page_id = ? AND ccc_binary = 1;'
        cursor.executemany(query,main_territory_list)
        conn.commit()

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)


# Calculates the number of strategies used to retrieve and introduce them into the database.
def calculate_articles_ccc_retrieval_strategies(languagecode):

    function_name = 'calculate_articles_ccc_retrieval_strategies '+languagecode
    if create_function_account_db(function_name, 'check','')==1: return

    functionstartTime = time.time()

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    conn2 = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor2 = conn.cursor()

    strategies = []
    query = 'SELECT qitem, page_id, geocoordinates, country_wd, location_wd, language_strong_wd, created_by_wd, part_of_wd, keyword_title, category_crawling_territories, language_weak_wd, affiliation_wd, has_part_wd, num_inlinks_from_CCC, num_outlinks_to_CCC FROM '+languagecode+'wiki'+';'
    for row in cursor.execute(query):
        num_retrieval_strategies = sum(x is not None for x in row)-2
        qitem = str(row[0])
        page_id = row[1]
        strategies.append((num_retrieval_strategies, qitem, page_id))
    query = 'UPDATE '+languagecode+'wiki SET num_retrieval_strategies = ? WHERE qitem = ? AND page_id = ?;'
    cursor.executemany(query,strategies)
    conn.commit()

    print ('CCC number of retrieval strategies for each Article assigned.')

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)


# CCC VERIFICATION TOOLS FUNCTIONS
#############################################

# Filter: Deletes all the CCC selected qitems from a language which are geolocated but not among the geolocated Articles to the territories associated to that language.
def groundtruth_reaffirmation(languagecode):

    function_name = 'groundtruth_reaffirmation '+languagecode
#    if create_function_account_db(function_name, 'check','')==1: return

    functionstartTime = time.time()
    conn2 = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor2 = conn2.cursor()

#    print ('cleant. NOW WE STaRT.')
#    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = NULL;'
#    cursor2.execute(query);
#    conn2.commit()

    # POSITIVE GROUNDTRUTH
    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 1 WHERE ccc_geolocated=1;'
    cursor2.execute(query);
    conn2.commit()
    print ('geolocated in, done.')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 1 WHERE country_wd IS NOT NULL;'
    cursor2.execute(query);
    conn2.commit()
    print ('country_wd, done.')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 1 WHERE location_wd IS NOT NULL;'
    cursor2.execute(query);
    conn2.commit()
    print ('location_wd, done.')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 1 WHERE language_strong_wd IS NOT NULL;'
    cursor2.execute(query);
    conn2.commit()
    print ('language_strong_wd, done.')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 1 WHERE created_by_wd IS NOT NULL;'
    cursor2.execute(query);
    conn2.commit()
    print ('created_by_wd, done.')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 1 WHERE part_of_wd IS NOT NULL;'
    cursor2.execute(query);
    conn2.commit()
    print ('part_of_wd, done.')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 1 WHERE keyword_title IS NOT NULL;'
    cursor2.execute(query);
    conn2.commit()
    print ('keyword_title, done.')


    # NEGATIVE GROUNDTRUTH
    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 0 WHERE ccc_geolocated=-1;'
    cursor2.execute(query);
    conn2.commit()
    print ('geolocated abroad, done.')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 0 WHERE other_ccc_location_wd IS NOT NULL;'
    cursor2.execute(query);
    conn2.commit()
    print ('location wikidata property abroad, done.')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = 0 WHERE other_ccc_country_wd IS NOT NULL AND country_wd IS NULL;'
    cursor2.execute(query);
    conn2.commit()
    print ('country wikidata property abroad, done.')

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)


def check_current_groundtruth(languagecode):

    functionstartTime = time.time()
    print ('\n* Check the ccc_binary from all the Articles from language: '+languages.loc[languagecode]['languagename']+' '+languagecode+'.')

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()

    print ('These are the ccc_binary null, zero and one: ')
    query = 'SELECT ccc_binary, count(*) FROM '+languagecode+'wiki GROUP BY ccc_binary;'
    for row in cursor.execute(query):
        print (row[0],row[1])

    ## BINARY 0
    print ('\nFor those that are ZERO:')
    print ('- geolocated:')
    query = 'SELECT ccc_geolocated, count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 0 GROUP BY ccc_geolocated;'
    for row in cursor.execute(query):
        print (row[0],row[1])

    print ('- other_ccc_location_wd:')
    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 0 AND other_ccc_location_wd IS NOT NULL;'
    for row in cursor.execute(query):
        print (row[0])

    print ('- other_ccc_country_wd:')
    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 0 AND other_ccc_country_wd IS NOT NULL;'
    for row in cursor.execute(query):
        print (row[0])

    ## BINARY 1
    print ('\nFor those that are ONE:')
    print ('- geolocated:')
    query = 'SELECT ccc_geolocated, count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 1 GROUP BY ccc_geolocated;'
    for row in cursor.execute(query):
        print (row[0],row[1])

    print ('- country_wd:')
    query = 'SELECT country_wd, count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 1 AND country_wd IS NOT NULL;'
    for row in cursor.execute(query):
        print (row[0])

    print ('- location_wd:')
    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 1 AND location_wd IS NOT NULL;'
    for row in cursor.execute(query):
        print (row[0])

    print ('- language_strong_wd:')
    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 1 AND language_strong_wd IS NOT NULL;'
    for row in cursor.execute(query):
        print (row[0])

    print ('- created_by_wd:')
    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 1 AND created_by_wd IS NOT NULL;'
    for row in cursor.execute(query):
        print (row[0])

    print ('- part_of_wd:')
    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 1 AND part_of_wd IS NOT NULL;'
    for row in cursor.execute(query):
        print (row[0])

    print ('- keyword_title:')
    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary = 1 AND keyword_title IS NOT NULL;'
    for row in cursor.execute(query):
        print (row[0])

    print ('\nFor those that are POTENTIAL ONE, we check the distribution of features in ccc_binary:')
    print ('- category_crawling:')
    query = 'SELECT ccc_binary, count(*) FROM '+languagecode+'wiki WHERE category_crawling_level IS NOT NULL GROUP BY ccc_binary;'
    for row in cursor.execute(query):
        print (row[0],row[1])

    print ('- language_weak_wd:')
    query = 'SELECT ccc_binary, count(*) FROM '+languagecode+'wiki WHERE language_weak_wd IS NOT NULL GROUP BY ccc_binary;'
    for row in cursor.execute(query):
        print (row[0],row[1])

    print ('- affiliation_wd:')
    query = 'SELECT ccc_binary, count(*) FROM '+languagecode+'wiki WHERE affiliation_wd IS NOT NULL GROUP BY ccc_binary;'
    for row in cursor.execute(query):
        print (row[0],row[1])

    print ('- has_part_wd:')
    query = 'SELECT ccc_binary, count(*) FROM '+languagecode+'wiki WHERE has_part_wd IS NOT NULL GROUP BY ccc_binary;'
    for row in cursor.execute(query):
        print (row[0],row[1])


def evaluate_content_selection_manual_assessment(languagecode, selected, page_titles_page_ids):

    print("start the CONTENT selection manual assessment ")

    if selected is None:
        print ('Retrieving the CCC Articles from the .db')
        conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
        query = 'SELECT * FROM '+languagecode+'wiki WHERE ccc_binary IS NOT NULL;'
        ccc_df = pd.read_sql_query(query, conn)
        ccc_df = ccc_df[['page_title','category_crawling_territories','category_crawling_level','language_weak_wd','affiliation_wd','has_part_wd','num_inlinks_from_CCC','num_outlinks_to_CCC','percent_inlinks_from_CCC','percent_outlinks_to_CCC','ccc_binary']]
        ccc_df = ccc_df.set_index(['page_title'])
        ccc_df = ccc_df.sample(frac=1) # randomize the rows order

        ccc_df_yes = ccc_df.loc[ccc_df['ccc_binary'] == 1]
        ccc_df_no = ccc_df.loc[ccc_df['ccc_binary'] == 0]

        sample = 100
        ccc_df_list_yes = ccc_df_yes.index.tolist()[:sample]
        ccc_df_list_no = ccc_df_no.index.tolist()[:sample]

        """
        output_file_name = 'ccc_assessment.txt'
        output_file_name_general1 = open(output_file_name, 'w')
        output_file_name_general1.write(', '.join('"{0}"'.format(w) for w in ccc_df_list_yes))
        output_file_name_general1.write(', '.join('"{0}"'.format(w) for w in ccc_df_list_no))
        """

        print ('ccc_df_list_yes=')
        print (ccc_df_list_yes)

        print ('ccc_df_list_no=')
        print (ccc_df_list_no)

        return # we return because this is actually run in another file: ccc_manual_assessment.py as it is not possible to open browsers via ssh.

        binary_list = sample*['c']+sample*['w']

        ccc_df_list = ccc_df_list_yes + ccc_df_list_no
        samplearticles=dict(zip(ccc_df_list,binary_list))

    else:
        page_ids_page_titles = {v: k for k, v in page_titles_page_ids.items()}

        print ('Using the CCC Articles that have just been classified.')
        conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
        query = 'SELECT * FROM '+languagecode+'wiki WHERE ccc_binary IS NOT NULL;'
        ccc_df = pd.read_sql_query(query, conn)
        ccc_df = ccc_df[['page_title','category_crawling_territories','category_crawling_level','language_weak_wd','affiliation_wd','has_part_wd','num_inlinks_from_CCC','num_outlinks_to_CCC','percent_inlinks_from_CCC','percent_outlinks_to_CCC','ccc_binary']]
        ccc_df = ccc_df.set_index(['page_title'])
#        ccc_df = ccc_df.sample(frac=1) # randomize the rows order

        ccc_df_yes = ccc_df.loc[ccc_df['ccc_binary'] == 1]

        new = []
        for x in selected: new.append(page_ids_page_titles[x[0]])
        ccc_df_list_yes = ccc_df_yes.index.tolist() + new
        ass = random.sample(ccc_df_list_yes, len(ccc_df_list_yes))
        ass = random.sample(ass, len(ass)); ass = random.sample(ass, len(ass))
        ccc_df_list_yes = ass
#        print (len(ccc_df_list_yes))

        ccc_df_no = page_titles_page_ids
        for x in ccc_df_list_yes: del ccc_df_no[x]
        ccc_df_list_no = list(ccc_df_no.keys())
        ass = random.sample(ccc_df_list_no, len(ccc_df_list_no))
        ass = random.sample(ass, len(ass)); ass = random.sample(ass, len(ass))
        ccc_df_list_no = ass
#        print (len(ccc_df_list_no))

        sample = 50
        ccc_df_list_yes = ccc_df_list_yes[:sample]
        ccc_df_list_no = ccc_df_list_no[:sample]

        print (ccc_df_list_yes)
        print (ccc_df_list_no)

        return # we return because this is actually run in another file: ccc_manual_assessment.py as it is not possible to open browsers via ssh.

        binary_list = sample*['c']+sample*['w']
        ccc_df_list = ccc_df_list_yes + ccc_df_list_no
        samplearticles=dict(zip(ccc_df_list,binary_list))

#        print (ccc_df_list)
#        print (samplearticles)
#        print (len(samplearticles))

    print ('The Articles are ready for the manual assessment.')
    ccc_df_list = random.shuffle(ccc_df_list)
    testsize = 200
    CCC_falsepositive = 0
    WP_falsenegative = 0

    counter = 1
    for title in samplearticles.keys():

        page_title = title
        wiki_url = urllib.parse.urljoin(
            'https://%s.wikipedia.org/wiki/' % (languagecode,),
            urllib.parse.quote_plus(page_title.encode('utf-8')))
        translate_url = urllib.parse.urljoin(
            'https://translate.google.com/translate',
            '?' + urllib.parse.urlencode({
                'hl': 'en',
                'sl': 'auto',
                'u': wiki_url,
            }))
        print (str(counter)+'/'+str(testsize)+' '+translate_url)
    #    webbrowser.open_new(wiki_url)
        webbrowser.open_new(translate_url)

        answer = input()

        if (answer != samplearticles[title]) & (samplearticles[title]=='c'): # c de correct
            CCC_falsepositive = CCC_falsepositive + 1
    #        print 'CIRA fals positiu'
        if (answer != samplearticles[title]) & (samplearticles[title]=='w'):  # w de wrong
            WP_falsenegative = WP_falsenegative + 1
    #        print 'WP fals negatiu'

        counter=counter+1

    result = 'WP '+languagecode+'wiki, has these false negatives: '+str(WP_falsenegative)+', a ratio of: '+str((float(WP_falsenegative)/100)*100)+'%.'+'\n'
    result = result+'CCC from '+languagecode+'wiki, has these false positives: '+str(CCC_falsepositive)+', a ratio of: '+str((float(CCC_falsepositive)/100)*100)+'%.'+'\n'
    print (result)




def create_update_qitems_single_ccc_table():

    function_name = 'create_update_qitems_single_ccc_table'
#    if create_function_account_db(function_name, 'check','')==1: return

    functionstartTime = time.time()

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()

    query = 'DROP TABLE IF EXISTS qitems_lang_ccc;'
    cursor.execute(query)
    conn.commit()

    query = ('CREATE table if not exists qitems_lang_ccc ('+
    'qitem text primary key,'+
    'langs text'+')')
    cursor.execute(query)
    conn.commit()

    qitems_langs = {} 
    for languagecode in wikilanguagecodes:
        print(languagecode)
        query = 'SELECT qitem FROM '+languagecode+'wiki WHERE ccc_binary = 1;'
        i=0
        for row in cursor.execute(query): 
            i+=1
            qitem = row[0]
            try:
                langs = qitems_langs[qitem]
                qitems_langs[qitem] = langs + '\t' + languagecode
            except:
                qitems_langs[qitem] = languagecode
        print(i)
    params = []
    for qitem, langs in qitems_langs.items():
        params.append((qitem, langs))

    query = 'INSERT OR IGNORE INTO qitems_lang_ccc (qitem, langs) values (?,?)'
    cursor.executemany(query, params); # to top_diversity_articles.db
    conn.commit()

    for languagecode in wikilanguagecodes:
        query = "SELECT COUNT(*) FROM "+languagecode+"wiki INNER JOIN qitems_lang_ccc on "+languagecode+"wiki.qitem = qitems_lang_ccc.qitem WHERE "+languagecode+"wiki.ccc_binary=0;"
        cursor.execute(query)
        value = cursor.fetchone()
        print (languagecode)
        if value != None: 
            print(value[0])

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)


    

def restore_ccc_binary_create_old_ccc_binary(languagecode,file):
#    print("start the CONTENT selection restore to the original ccc binary for language: "+languagecode)

    functionstartTime = time.time()

    if file == 1:
        filename = databases_path + 'old_ccc/' + languagecode+'_old_ccc.csv'
        output_file = codecs.open(filename, 'a', 'UTF-8')

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    query = 'SELECT qitem, page_id, ccc_geolocated, country_wd, location_wd, language_strong_wd, created_by_wd, part_of_wd, keyword_title, ccc_binary FROM '+languagecode+'wiki;'

    parameters = []
    for row in cursor.execute(query):
        qitem = row[0]
        page_id = row[1]
        ccc_binary = None
        main_territory = None

        ccc_geolocated = row[2]
        if ccc_geolocated == 1: ccc_binary = 1;
        if ccc_geolocated == -1: ccc_binary = 0;

        for x in range(3,len(row)-2):
            if row[x] != None: ccc_binary = 1

#        print ((ccc_binary,main_territory,qitem,page_id))
        parameters.append((ccc_binary,main_territory,qitem,page_id))

        cur_ccc_binary = row[9]
        if file == 1: output_file.write(qitem + '\t' + str(cur_ccc_binary) + '\n')

    query = 'UPDATE '+languagecode+'wiki SET ccc_binary = ?, main_territory = ? WHERE qitem = ? AND page_id = ?;'
    cursor.executemany(query,parameters)
    conn.commit()

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))


def check_current_ccc_binary_old_ccc_binary(languagecode):
#    print("compare current ccc with a previous one.")

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()

    old_ccc_file_name = databases_path + 'old_ccc/' + languagecode+'_old_ccc.csv'
    old_ccc_file = open(old_ccc_file_name, 'r')    
    old_ccc = {}
    old_number_ccc = 0
    for line in old_ccc_file: # dataset
        page_data = line.strip('\n').split('\t')
#        page_data = line.strip('\n').split(',')
        ccc_binary = str(page_data[1])
        qitem = page_data[0]
        qitem=str(qitem)
        old_ccc[qitem] = ccc_binary
        if ccc_binary == 1: old_number_ccc+=1

    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary=1;'
    cursor.execute(query)
    current_number_ccc=cursor.fetchone()[0]

    print ('In old CCC there were: '+str(old_number_ccc)+' Articles, a percentage of '+str(float(100*old_number_ccc/wikipedialanguage_numberarticles[languagecode])))
    print ('In current CCC there are: '+str(current_number_ccc)+' Articles, a pecentage of '+str(float(100*current_number_ccc/wikipedialanguage_numberarticles[languagecode])))

    print ('\nProceeding now with the Article comparison: ')

    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
#    query = 'SELECT qitem, page_id, page_title, ccc_binary FROM '+languagecode+'wiki;'
    query = 'SELECT qitem, page_id, page_title, ccc_binary, category_crawling_territories, language_weak_wd, affiliation_wd, has_part_wd, num_inlinks_from_CCC, num_outlinks_to_CCC, percent_inlinks_from_CCC, percent_outlinks_to_CCC, other_ccc_country_wd, other_ccc_location_wd, other_ccc_language_strong_wd, other_ccc_created_by_wd, other_ccc_part_of_wd, other_ccc_language_weak_wd, other_ccc_affiliation_wd, other_ccc_has_part_wd, other_ccc_keyword_title, other_ccc_category_crawling_relative_level, num_inlinks_from_geolocated_abroad, num_outlinks_to_geolocated_abroad, percent_inlinks_from_geolocated_abroad, percent_outlinks_to_geolocated_abroad FROM '+languagecode+'wiki;'

    i = 0
    j = 0

    for row in cursor.execute(query):
        qitem = row[0]
        page_id = str(row[1])
        page_title = row[2]

        ccc_binary = row[3]
        if ccc_binary == None or ccc_binary == 'None': ccc_binary = 0
        if ccc_binary == '1': ccc_binary = 1

        category_crawling_territories = str(row[4])
        language_weak_wd = str(row[5])
        affiliation_wd = str(row[6])
        has_part_wd = str(row[7])
        num_inlinks_from_CCC = str(row[8])
        num_outlinks_to_CCC = str(row[9])
        percent_inlinks_from_CCC = str(row[10])
        percent_outlinks_to_CCC = str(row[11])
        other_ccc_country_wd = str(row[12])
        other_ccc_location_wd = str(row[13])
        other_ccc_language_strong_wd = str(row[14])
        other_ccc_created_by_wd = str(row[15])
        other_ccc_part_of_wd = str(row[16])
        other_ccc_language_weak_wd = str(row[17])
        other_ccc_affiliation_wd = str(row[18])
        other_ccc_has_part_wd = str(row[19])
        other_ccc_keyword_title = str(row[20])
        other_ccc_category_crawling_relative_level = str(row[21])
        num_inlinks_from_geolocated_abroad = str(row[22])
        num_outlinks_to_geolocated_abroad = str(row[23])
        percent_inlinks_from_geolocated_abroad = str(row[24])
        percent_outlinks_to_geolocated_abroad = str(row[25])

        old_ccc_binary = old_ccc[qitem]
        if old_ccc_binary == None or old_ccc_binary == 'None': old_ccc_binary = 0
        if old_ccc_binary == '1' or old_ccc_binary == 1: old_ccc_binary = 1

        line = page_title+' , '+page_id+'\n\tcategory_crawling_territories\t'+category_crawling_territories+'\tlanguage_weak_wd\t'+language_weak_wd+'\taffiliation_wd\t'+affiliation_wd+'\thas_part_wd\t'+has_part_wd+'\tnum_inlinks_from_CCC\t'+num_inlinks_from_CCC+'\tnum_outlinks_to_CCC\t'+num_outlinks_to_CCC+'\tpercent_inlinks_from_CCC\t'+percent_inlinks_from_CCC+'\tpercent_outlinks_to_CCC\t'+percent_outlinks_to_CCC+'\tother_ccc_country_wd\t'+other_ccc_country_wd+'\tother_ccc_location_wd\t'+other_ccc_location_wd+'\tother_ccc_language_strong_wd\t'+other_ccc_language_strong_wd+'\tother_ccc_created_by_wd\t'+other_ccc_created_by_wd+'\tother_ccc_part_of_wd\t'+other_ccc_part_of_wd+'\tother_ccc_language_weak_wd\t'+other_ccc_language_weak_wd+'\tother_ccc_affiliation_wd\t'+other_ccc_affiliation_wd+'\tother_ccc_has_part_wd\t'+other_ccc_has_part_wd+'\tother_ccc_keyword_title\t'+other_ccc_keyword_title+'\tother_ccc_category_crawling_relative_level\t'+other_ccc_category_crawling_relative_level+'\tnum_inlinks_from_geolocated_abroad\t'+num_inlinks_from_geolocated_abroad+'\tnum_outlinks_to_geolocated_abroad\t'+num_outlinks_to_geolocated_abroad+'\tpercent_inlinks_from_geolocated_abroad\t'+percent_inlinks_from_geolocated_abroad+'\tpercent_outlinks_to_geolocated_abroad\t'+percent_outlinks_to_geolocated_abroad

#        if ccc_binary == 1: 

        if ccc_binary == 1 and old_ccc_binary == 0:
            print ('* '+line + '\n old_ccc_binary: '+str(old_ccc_binary)+', ccc_binary: '+str(ccc_binary))
            print ('now ccc (only positive), before non-ccc'+'\n')
            j += 1

        if ccc_binary == 0 and old_ccc_binary == 1:
            print ('* '+line + '\n old_ccc_binary: '+str(old_ccc_binary)+', ccc_binary: '+str(ccc_binary))
            print ('before ccc (with positive and negative), now non-ccc'+'\n')
            i += 1

    print ("*\n")
    print ("There are "+str(i)+" Articles that are non-CCC now but they were.")
    print ("There are "+str(j)+" Articles that are CCC now but they were non-CCC before.")
    print ("* End of the comparison")





# Creates a dataset from the CCC database for a list of languages.
# COMMAND LINE: sqlite3 -header -csv ccc_temp.db "SELECT * FROM ccc_cawiki;" > ccc_cawiki.csv
def extract_ccc_tables_to_files():
    function_name = 'extract_ccc_tables_to_files'
    if create_function_account_db(function_name, 'check','')==1: return

    functionstartTime = time.time()

    for languagecode in wikilanguagecodes:
        conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()

        # These are the folders.
        superfolder = datasets_path+cycle_year_month
        languagefolder = superfolder+'/'+languagecode+'wiki/'
        latestfolder = datasets_path+'latest/'
        if not os.path.exists(languagefolder): os.makedirs(languagefolder)
        if not os.path.exists(latestfolder): os.makedirs(latestfolder)

        # These are the files.
        ccc_filename_archived = languagecode + 'wiki_' + str(cycle_year_month.replace('-',''))+'_ccc.csv' # (e.g. 'cawiki_20180215_ccc.csv')
        ccc_filename_latest = languagecode + 'wiki_latest_ccc.csv.bz2' # (e.g. cawiki_latest_ccc.csv)

        # These are the final paths and files.
        path_latest = latestfolder + ccc_filename_latest
        path_language = languagefolder + ccc_filename_archived
        print ('Extracting the CCC from language '+languagecode+' into the file: '+path_language)
        print ('This is the path for the latest files altogether: '+path_latest)

        # Here we prepare the streams.
        path_language_file = codecs.open(path_language, 'w', 'UTF-8')
        c = csv.writer(open(path_language,'w'), lineterminator = '\n', delimiter='\t')

        # Extract database into a dataset file. Only the rows marked with CCC.
#        cursor.execute("SELECT * FROM "+languagecode+"wiki WHERE ccc_binary = 1;") # 
        cursor.execute("SELECT * FROM "+languagecode+"wiki;") # ->>>>>>> canviar * per les columnes. les de rellevància potser no cal.

        i = 0
        c.writerow([d[0] for d in cursor.description])
        for result in cursor:
            i+=1
            c.writerow(result)

        compressionLevel = 9
        source_file = path_language
        destination_file = source_file+'.bz2'

        tarbz2contents = bz2.compress(open(source_file, 'rb').read(), compressionLevel)
        fh = open(destination_file, "wb")
        fh.write(tarbz2contents)
        fh.close()

        print (languagecode+' language CCC has this number of rows: '+str(i))
        # Delete the old 'latest' file and copy the new language file as a latest file.

        try:
            os.remove(path_language);
            os.remove(path_latest); 
        except: pass
        cursor.close()

        shutil.copyfile(destination_file,path_latest)
        print ('Creating the latest_file for: '+languagecode+' with name: '+path_latest)

        # Count the number of files in the language folders and in case they are more than X, we delete them.
#        filenamelist = sorted(os.listdir(languagefolder), key = os.path.getctime)

        # Reference Datasets:
        # http://whgi.wmflabs.org/snapshot_data/
        # https://dumps.wikimedia.org/wikidatawiki/entities/
        # http://ftp.acc.umu.se/mirror/wikimedia.org/dumps/cawiki/20180201/
    
    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)


def extract_ccc_google_schema_json():
    function_name = 'extract_ccc_google_schema_json'
    if create_function_account_db(function_name, 'check','')==1: return

    functionstartTime = time.time()

    current = cycle_year_month
    data = {
      "@context":"http://schema.org/",
      "@type":"Dataset",
      "name":"Wikipedia Cultural Context Content Dataset",
      "description":"Cultural Context Content is the group of Articles in a Wikipedia language edition that relates to the editors' geographical and cultural context (places, traditions, language, politics, agriculture, biographies, events, etcetera.). Cultural Context Content is collected as a dataset, which is available in a monthly basis, and allows the Wikipedia Cultural Diversity Observatory project to show and depict several statistics on the state of knowledge equality and cross-cultural coverage. These datasets are computed for all Wikipedia language editions. They allow answering questions such as: \n* How self-centered any Wikipedia is (the extent of ccc as percentage and number of Articles)? Are the CCC Articles responding to readers demand for information?\n* How well any Wikipedia covers the existing world cultural diversity (gaps)?\n* Are the Articles created each month dedicated to fill these gaps?\n* Which are the most relevant Articles from each Wikipedia’s related cultural context and particular topics?",
      "url":"https://wcdo.wmflabs.org/datasets/",
      "sameAs":"https://meta.wikimedia.org/wiki/Wikipedia_Cultural_Diversity_Observatory/Cultural_Context_Content#Datasets",
      "license": "Creative Commons CC0 dedication",
      "keywords":[
         "Content Imbalances > Language Gap > Culture gap",
         "Online Communities > Wikipedia > Wiki Studies",
         "Cultural Diversity > Cross-cultural data",
         "Big Data > Data mining > Public repositories"
      ],
      "creator":{
         "@type":"Organization",
         "url": "https://meta.wikimedia.org/wiki/Wikipedia_Cultural_Diversity_Observatory",
         "name":"Wikipedia Cultural Diversity Observatory",
         "contactPoint":{
            "@type":"ContactPoint",
            "contactType": "customer service",
            "email":"tools.wcdo@tools.wmflabs.org"
         }
      },
      "includedInDataCatalog":{
         "@type":"Wikimedia datasets",
         "name":"https://meta.wikimedia.org/wiki/Datasets"
      },
      "distribution":[
         {
            "@type":"DataDownload",
            "encodingFormat":"CSV",
         },
      ],
      "temporalCoverage":"2001-01-01/2018-"+cycle_year_month
    }

    with open(datasets_path+'/latest/'+'CCC_datasets.json', 'w') as f:
      json.dump(data, f, ensure_ascii=False)
      
    """
    https://developers.google.com/search/docs/data-types/dataset
    https://www.blog.google/products/search/making-it-easier-discover-datasets/amp/ 
    https://search.google.com/structured-data/testing-tool
    https://toolbox.google.com/datasetsearch
    """

    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    create_function_account_db(function_name, 'mark', duration)


def extract_ccc_count(languagecode, filename, message):
    conn = sqlite3.connect(databases_path + wikipedia_diversity_db); cursor = conn.cursor()
    query = 'SELECT count(*) FROM '+languagecode+'wiki WHERE ccc_binary=1;'
    cursor.execute(query)
    row = cursor.fetchone()
    if row: row1 = str(row[0]);

    query = 'SELECT count(*) FROM '+languagecode+'wiki;'
    cursor.execute(query)
    row = cursor.fetchone()
    if row: row2 = str(row[0]);

    languagename = languages.loc[languagecode]['languagename']

    with open(filename, 'a') as f:
        f.write(languagename+'\t'+message+'\t'+row1+'\t'+row2+'\n')


#######################################################################################


def main_with_exception_email():
    try:
        main()
    except:
    	wikilanguages_utils.send_email_toolaccount('WCDO - CONTENT SELECTION ERROR: '+ wikilanguages_utils.get_current_cycle_year_month(), 'ERROR.')


def main_loop_retry():
    page = ''
    while page == '':
        try:
            main()
            page = 'done.'
        except:
            print('There was an error in the main. \n')
            path = '/srv/wcdo/src_data/content_selection.err'
            file = open(path,'r')
            lines = file.read()
            wikilanguages_utils.send_email_toolaccount('WCDO - CONTENT SELECTION ERROR: '+ wikilanguages_utils.get_current_cycle_year_month(), 'ERROR.' + lines); print("Now let's try it again...")
            time.sleep(900)
            continue


######################################################################################

class Logger_out(object): # this prints both the output to a file and to the terminal screen.
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("content_selection"+".out", "w")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        pass
class Logger_err(object): # this prints both the output to a file and to the terminal screen.
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("content_selection"+".err", "w")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        pass


### MAIN:
if __name__ == '__main__':
    sys.stdout = Logger_out()
    sys.stderr = Logger_err()

    script_name = 'content_selection.py'
    cycle_year_month = wikilanguages_utils.get_current_cycle_year_month()
#    check_time_for_script_run(script_name, cycle_year_month)
    startTime = time.time()

    territories = wikilanguages_utils.load_wikipedia_languages_territories_mapping()
    languages = wikilanguages_utils.load_wiki_projects_information();


    wikilanguagecodes = sorted(languages.index.tolist())
    print ('checking languages Replicas databases and deleting those without one...')
    # Verify/Remove all languages without a replica database
    for a in wikilanguagecodes:
        if wikilanguages_utils.establish_mysql_connection_read(a)==None:
            wikilanguagecodes.remove(a)
    print (wikilanguagecodes)
    print (len(wikilanguagecodes))

    languageswithoutterritory=['eo','got','ia','ie','io','jbo','lfn','nov','vo']

    # Get the number of Articles for each Wikipedia language edition
    wikipedialanguage_numberarticles = wikilanguages_utils.load_wikipedia_language_editions_numberofarticles(wikilanguagecodes,'')
#    print (wikilanguagecodes)
    
    wikilanguagecodes_by_size = [k for k in sorted(wikipedialanguage_numberarticles, key=wikipedialanguage_numberarticles.get, reverse=True)]
    biggest = wikilanguagecodes_by_size[:20]; smallest = wikilanguagecodes_by_size[20:]


     wikilanguages_utils.verify_script_run(cycle_year_month, script_name, 'check', '')
    main()
#    main_with_exception_email()
#    main_loop_retry()
    duration = str(datetime.timedelta(seconds=time.time() - functionstartTime))
    wikilanguages_utils.verify_script_run(cycle_year_month, script_name, 'mark', duration)


    wikilanguages_utils.finish_email(startTime,'content_selection.out','Content Selection')
