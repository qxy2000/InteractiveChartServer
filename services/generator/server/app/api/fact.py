from flask_restful import Resource, reqparse
import json
import requests
from ..algorithm.fact import fact_scoring
from ..algorithm import RandomGenerator, FactFactory, load_df
from flask import request
import logging
from ast import literal_eval
import pandas as pd
from copy import copy
import numpy 

class Fact(Resource):
  
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
        parser = reqparse.RequestParser()
        parser.add_argument('file_name', required=True, help="file_name cannot be blank!")
        parser.add_argument('fact', required=True, help="fact cannot be blank!")
        parser.add_argument('filters', default='nofilter', help="filter or nofilter")
        parser.add_argument('method', required=True, help="method cannot be blank!")
        args = parser.parse_args()

        ip = request.remote_addr
        if request.headers.getlist("X-Real-IP"):
            ip = request.headers.getlist("X-Real-IP")[0]

        file_path = 'http://fileserver:6008/data/%s'%(args['file_name'])
        schema_path='http://fileserver:6008/data/%s.json'%(args['file_name'][:-4])
        # file_path = 'http://localhost:6008/data/%s'%(args['file_name'])
        # schema_path='http://localhost:6008/data/%s.json'%(args['file_name'][:-4])

        df = load_df(file_path)
         # May 24, 2021. Add filter to df. Menndy
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
        if df is None:
            return {
                'score': 0,
                'parameter': '',
                'possibility': 0,
                'information': 0,
                'significance': 0,
                'fact': {},
            }

        fact = json.loads(args['fact'])
        # print(fact)
        # method = args['method']
        method = 'sig'

        score, parameter, possibility, information, significance = fact_scoring(fact, df, schema, method)
        fact['score'] = score
        # print(fact['score'])
        fact['parameter'] = parameter

        return {
            'score': score,
            'parameter': parameter,
            'possibility': possibility,
            'information': information,
            'significance': significance,
            'fact': fact,
        }