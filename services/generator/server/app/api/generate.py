import os
import pandas as pd
import json
import jsonpickle
import requests
import random
import warnings
import logging
from flask_restful import Resource, reqparse
from ..algorithm import RandomGenerator, MCTSGenerator, FactFactory, load_df
from flask import request
from ast import literal_eval
from copy import copy
import numpy 

def exists(path):
    r = requests.head(path)
    return r.status_code == requests.codes.ok

class Generate(Resource):

    def __init__(self):
        logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO, filename="calliope-lite.log", filemode="a")

    def df_filter(self, df, filters):
        new_df = df.copy()
        filters=literal_eval(str(filters))
        for flter in filters:           
            if flter['type'] == 'equal':
                try:
                    new_df = new_df[new_df[flter['field']].isin([pd.to_datetime(x, format="%Y/%m/%d") for x in flter['value']])]
                except:
                    try:
                        new_df = new_df[new_df[flter['field']].isin([float(x) for x in flter['value']])]
                    except:
                        new_df = new_df[new_df[flter['field']].isin(flter['value'])]   

            elif flter['type'] == 'greater':
                try:
                    new_df = new_df[new_df[flter['field']] > float(flter['value'][0])]
                except:
                    new_df = new_df[new_df[flter['field']] > pd.to_datetime(flter['value'][0], format="%Y/%m/%d")]
            
            elif flter['type'] == 'smaller':
                try:
                    new_df = new_df[new_df[flter['field']] < float(flter['value'][0])]
                except:
                    new_df = new_df[new_df[flter['field']] < pd.to_datetime(flter['value'][0], format="%Y/%m/%d")]
            
            elif flter['type'] == 'between':
                try:
                    new_df = new_df[new_df[flter['field']].between(float(flter['value'][0]),float(flter['value'][1]))]
                except:
                    new_df = new_df[new_df[flter['field']].between(pd.to_datetime(flter['value'][0], format="%Y/%m/%d"),pd.to_datetime(flter['value'][1], format="%Y/%m/%d"))]
                
            elif flter['type'] == 'greaterequal':
                try:
                    new_df = new_df[new_df[flter['field']] >= float(flter['value'][0])]
                except:
                    
                    new_df = new_df[new_df[flter['field']] >= pd.to_datetime(flter['value'][0], format="%Y/%m/%d")]
            
            elif flter['type'] == 'smallerequal':
                try:
                    new_df = new_df[new_df[flter['field']] <= float(flter['value'][0])]
                except:
                    new_df = new_df[new_df[flter['field']] <= pd.to_datetime(flter['value'][0], format="%Y/%m/%d")]
        return new_df

    def schema_filter(self, schema, filters):
        new_schema = copy(schema)
        filters=literal_eval(str(filters))
        for field in new_schema['fields']:
            flters = [x for x in filters if x['field']==field['field']]
            if len(flters) == 0:
                continue
            for flter in flters:
                field['values'] = [x.replace(',','') for x in field['values']]
                if flter['type'] == 'equal':
                    field['values'] = flter['value']

                elif flter['type'] == 'greater':
                    try:
                        field['values'] = [x for x in field['values'] if float(x) > float(flter['value'][0])]
                    except:
                        field['values'] = [x for x in field['values'] if pd.to_datetime(x, format="%Y/%m/%d") > pd.to_datetime(flter['value'][0], format="%Y/%m/%d")]
                
                elif flter['type'] == 'smaller':
                    try:
                        field['values'] = [x for x in field['values'] if float(x) < float(flter['value'][0])]
                    except:
                        field['values'] = [x for x in field['values'] if pd.to_datetime(x, format="%Y/%m/%d") < pd.to_datetime(flter['value'][0], format="%Y/%m/%d")]
                
                elif flter['type'] == 'between':
                    try:
                        field['values'] = [x for x in field['values'] if (float(x) < float(flter['value'][1]) and float(x) > float(flter['value'][0]))]
                    except:
                        # print('---------------------------')
                        # print(type(flter['value'][0]))
                        # print('---------------------------')
                        field['values'] = [x for x in field['values'] if (pd.to_datetime(x, format="%Y/%m/%d") > pd.to_datetime(flter['value'][0], format="%Y/%m/%d")) and (pd.to_datetime(x, format="%Y/%m/%d") < pd.to_datetime(flter['value'][1], format="%Y/%m/%d"))]                
                
                elif flter['type'] == 'greaterequal':
                    try:
                        field['values'] = [x for x in field['values'] if float(x) >= float(flter['value'][0])]
                    except:
                        field['values'] = [x for x in field['values'] if pd.to_datetime(x, format="%Y/%m/%d") >= pd.to_datetime(flter['value'][0], format="%Y/%m/%d")]
                elif flter['type'] == 'smallerequal':
                    try:
                        field['values'] = [x for x in field['values'] if float(x) <= float(flter['value'][0])]
                    except:
                        field['values'] = [x for x in field['values'] if pd.to_datetime(x, format="%Y/%m/%d") <= pd.to_datetime(flter['value'][0], format="%Y/%m/%d")]

        return new_schema

    def post(self):
        warnings.filterwarnings("ignore")

        ip = request.remote_addr
        if request.headers.getlist("X-Real-IP"):
            ip = request.headers.getlist("X-Real-IP")[0]

        #
        # Parse request
        #
        parser = reqparse.RequestParser()
        parser.add_argument('file_name', required=True, help="file_name cannot be blank!")
        parser.add_argument('filters', default='nofilter', help="filter or nofilter")
        parser.add_argument('max_story_length', required=True, help="max_story_length cannot be blank!")
        parser.add_argument('method', default='random', help="generation method") # random or mcts
        args = parser.parse_args()

        max_story_length = int(args['max_story_length'])

        # April 14th 2021, remove the folder named by user ip, guoyi
        file_path = 'http://fileserver:6008/data/%s'%(args['file_name'])
        schema_path='http://fileserver:6008/data/%s.json'%(args['file_name'][:-4])
        # file_path = 'http://localhost:6008/data/%s'%(args['file_name'])
        # schema_path='http://localhost:6008/data/%s.json'%(args['file_name'][:-4])

        logging.info('[%s] starts insight extraction on [%s].'%(ip, args['file_name']))

        if not exists(file_path):
            logging.error('[%s] Generation failed! Cannot find [%s].'%(ip, args['file_name']))
            return {
                "error": "File does not exist"
            }

        if not exists(schema_path):
            logging.error('[%s] Generation failed! Cannot find [%s.json].'%(ip, args['file_name'][:-4]))
            return {
                "error": "schema does not exist"
            }

        #
        # Load file, 
        df = load_df(file_path)
        # April 15, 2021. Add filter to df. guoyi
        if args['filters'] != 'nofilter':
            df = self.df_filter(df,args['filters'])
        if df is None:
            logging.error('[%s] Generation failed due to the data is not in UTF-8 / GBK.'%ip)
            return {
                'fail': 'Fail to decode data. Please upload utf-8 file.'
            }

        schema=requests.get(schema_path).json()
        if args['filters'] != 'nofilter':
            schema = self.schema_filter(schema,args['filters'])


        if schema['statistics']['column'] < 2:
            logging.error('[%s] Generation failed! [%s] has less than two data columns.'%(ip,args['file_name']))
            return {
                'fail': 'We need at least two data columns to generate visual content.'
            }
        if schema['statistics']['numerical'] < 1:
            logging.error('[%s] Generation failed! [%s] contains no numerical columns.'%(ip,args['file_name']))
            return {
                'fail': 'We need at least one numerical column to generate visual content.'
            }
        if schema['statistics']['categorical'] + schema['statistics']['geographical'] + schema['statistics']['temporal'] < 1:
            logging.error('[%s] generation failed! [%s] contains no categorical/temporal/geographical columns.'%(ip, args['file_name']))
            return {
                'fail': 'We need at least one categorical/temporal/geographical column to generate visual content.'
            }

        #
        # Generator
        #
        if args['method'] == 'mcts':
            factory = FactFactory(df, schema)
            goal = {
                "limit": 1000,
                "length": max_story_length,
                "info": 50
            }
            reward = {
                'logicality': 0.2,
                'diversity': 0.3,
                'integrity': 0.5
            }
            tree = None
            generator = MCTSGenerator(df, schema, goal, reward, factory, tree)
            for _ in range(max_story_length):
                story, newtree = generator.generateIteratively()
                tree = newtree
            
            # print(newtree)
            return {
                "story": story
            }
        else:
            generator = RandomGenerator(df, schema)

            candidates = generator.generate()
            candidates = list(candidates)
            
            logging.info('[%s] sucessfully extracted [%d] data facts based on [%s] and [%d] most important ones are used.'%(ip, len(candidates), args['file_name'], max_story_length))
            
            if len(candidates) > max_story_length:
                candidates = random.sample(candidates, max_story_length)
                for candidate in candidates:
                    if isinstance(candidate["parameter"], float):
                        candidate["parameter"] = round(candidate["parameter"], 2)

            return {
                "story": {
                    "facts": candidates
                }
            }