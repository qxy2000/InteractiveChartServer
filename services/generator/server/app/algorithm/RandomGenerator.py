import copy
import random
import datetime
import multiprocessing
import numpy as np
import json as js

from .generator import Generator
from .fact import fact_scoring, fact_validation, fact_extraction, fact_focus

class RandomGenerator(Generator):
    def __init__(self, df, schema):
        self.df = df
        self.schema = schema
        self.processLock = multiprocessing.Lock()
        self.manager = multiprocessing.Manager()
        self.generatedFacts = self.manager.list()
        # self.random_policy = random.choice(['measure', 'subspace']) # measure or subspace
        self.random_policy = 'measure'
        print('#################################')
        print('current random policy: %s'%(self.random_policy))
        self.pool = {} # cache fact importance score

        # print(schema)

        # columns
        self.n_fields = self._filterfields(schema, 'numerical')
        self.c_fields = self._filterfields(schema, 'categorical')
        self.t_fields = self._filterfields(schema, 'temporal')
        self.g_fields = self._filterfields(schema, 'geographical')
        self.cg_fields = self.c_fields + self.g_fields
        self.ctg_fields = self.c_fields + self.t_fields + self.g_fields
        
        # enumarate measure
        self.measure_list = []
        for n_field in self.n_fields:
            for agg in n_field['aggregate']:
                self.measure_list.append([{'field': n_field['field'], 'subtype': n_field['subtype'], 'aggregate': str(agg)}])

        self.selected_measure = random.choice(self.measure_list)
        if self.random_policy == 'measure':
            print('#################################')
            print('selected measure: %s'%(self.selected_measure[0]['field']))
            print('#################################')

        # enumarate subspace
        self.subspace_list = []
        self.subspace_list.append([])
        for field in self.ctg_fields:
            if 'values' in field:
                for value in field['values']:
                    self.subspace_list.append([{'field':field['field'], 'value':value}])
        self.selected_subspace = random.choice(self.subspace_list)
        if self.random_policy == 'subspace':
            print('#################################')
            print('selected subspace: %s'%(self.selected_subspace))
            print('#################################')

    # 
    # Generate
    # 
    def generate(self):
        self.generateByParallel()

        if len(self.generatedFacts) == 0 and self.random_policy == 'subspace':
            self.random_policy = 'measure'
            print('#################################')
            print('failed to generate in selected subspace: %s'%(self.selected_subspace))
            print('#################################')
            print('switch random policy: %s'%(self.random_policy))
            print('#################################')
            print('selected measure: %s'%(self.selected_measure[0]['field']))
            print('#################################')
            self.generateByParallel()

        facts = list(self.generatedFacts)
        
        facts.sort(reverse=True, key=lambda x: x['score'])

        return facts

    # 
    # Create facts in parallel processes
    # 
    def generateByParallel(self):

        process_list = []
        for column in self.ctg_fields:
            process_list.append(multiprocessing.Process(target=self.generateRandomly, args=(column, 1000, )))
        for process in process_list:
            process.start()
        for process in process_list:
            process.join()

    # 
    # Create facts sequentially
    #      
    def generateSequentially(self):
        for column in self.ctg_fields:
            columnfield = column['field']
            self.generateRandomly(columnfield, 1000)

    # 
    # Create a set of facts randomly
    # 
    def generateRandomly(self, column, scale=1000):

        candidates = []
        for _ in range(scale):
            try:
                fact = self.generateByColumn(column)
                
                if fact == None:
                    continue
                
                candidates.append(fact)
            except:
                print(self.generateByColumn(column))
                continue
        candidates = list(filter(lambda x: self._validate(x), candidates)) # validation
        candidates = list(map(lambda x: self._calculate(x), candidates)) # score calulation
        candidates = list(filter(lambda x: x['significance']>0.05, candidates)) # filter low significance
        candidates.sort(reverse=True, key=lambda x: x['score'])
        self.processLock.acquire()
        print('add %s random facts in %s'%(len(candidates),column['field']))
        self.generatedFacts += candidates
        self.processLock.release()

        return candidates

    # 
    # Create a random fact by column
    # 
    def generateByColumn(self, column):
        
        # enumarate subspace
        column_subspace_list = []
        column_subspace_list.append([])
        if self.random_policy == 'subspace':
            column_subspace_list = [self.selected_subspace]
        else:
            if 'values' in column:
                for value in column['values']:
                    column_subspace_list.append([{'field':column['field'], 'value':value}])

        facttypes = ['outlier', 'proportion', 'extreme', 'difference','distribution', 'rank', 'categorization', 'trend', 'value']
        facttype = random.choice(facttypes)

        return self.generateByType(facttype, column_subspace_list)

    # 
    # Create a set of facts randomly by type
    # 
    def generateByType(self, facttype, subspace_list = []):
        if len(subspace_list) == 0:
            subspace_list = self.subspace_list
        facttypes_with_focus = ['outlier', 'proportion', 'extreme', 'difference']
        facttypes_without_focus = ['distribution', 'rank', 'categorization', 'association', 'trend', 'value']

        new_fact = {
            "type": facttype,
            "measure": [],
            "subspace": [],
            "groupby": [],
            "focus": []
        }

        # add groupby
        if facttype == 'trend':
            new_fact['groupby'] = [random.choice(self.t_fields)] if len(self.t_fields) > 0 else []
        elif facttype in ['categorization', 'distribution']:
            new_fact['groupby'] = [random.choice(self.cg_fields)] if len(self.cg_fields) > 0 else []
        elif facttype == 'value':
            new_fact['groupby'] = []
        elif facttype == 'proportion':
            new_fact['groupby'] = []
            f = random.choice(self.ctg_fields) if len(self.cg_fields) > 0 else None
            if f is not None and 'values' in f and len(f['values']) > 1:
                new_fact['groupby'] = [f]
        else:
            new_fact['groupby'] = [random.choice(self.ctg_fields)] if len(self.ctg_fields) > 0 else []

        # randomize fact measures
        m = random.choice(self.measure_list)[0]
        new_fact['measure'] = [{'field': m['field'], 'subtype': m['subtype'], 'aggregate': m['aggregate']}]
        if facttype == 'proportion':
            # in case of proportion, only the sum aggregation method makes some scense
            new_fact['measure'][0]['aggregate'] = 'sum'
            # in case of proportion, the field to be measured must only contain positive numbers
            if new_fact['measure'][0]['subtype'] in ['real', 'integer', 'real-', 'integer-']:
                new_fact['measure'] = []

        # add measure
        # if self.random_policy == 'measure':
        #     new_fact['measure'] = self.selected_measure
        # else:
        #     new_fact['measure'] = random.choice(self.measure_list)
        
        # add subspace
        new_fact['subspace'] = random.choice(subspace_list)

        # check if the breakdown field is unique or not
        if len(new_fact['groupby']) > 0:
            if new_fact['groupby'][0]['isUnique']:
                if len(new_fact['measure']) > 0: 
                    new_fact['measure'][0]['aggregate'] = ''
                new_fact['subspace'] = []
            new_fact['groupby'][0] = new_fact['groupby'][0]['field']

        # add focus
        if facttype in facttypes_with_focus:
            fact_df,_,_ = fact_extraction(new_fact, self.df)
            try:
                new_fact = fact_focus(new_fact, fact_df)
            except:
                # print('focus error')
                pass


        return self._jsonify(new_fact)

    def _filterfields(self, schema, dtype):
        if schema['statistics'][dtype] == 0:
            return []
        else:
            if dtype == 'geographical':
                return list(filter(lambda x: (x["type"] == dtype and not x["isPostCode"]) , schema['fields']))
            else:
                return list(filter(lambda x: (x["type"] == dtype) , schema['fields']))

    def _validate(self, fact):
        if fact_validation(fact, self.schema, self.df):
            return True
        else:
            return False

    def _calculate(self, fact):
        factid = hash(str(fact))
        if factid in self.pool:
            return self.pool[factid]
        else:
            fact_score, fact_parameter, fact_possibility, fact_information, fact_significance = fact_scoring(fact, self.df, self.schema)
            fact['score'] = fact_score
            fact['parameter'] = fact_parameter
            fact['possibility'] = fact_possibility
            fact['information'] = fact_information
            fact['significance'] = fact_significance
            self.pool[factid] = fact # add to pool
            return fact

    def _jsonify(self, fact):
        for i, focus in enumerate(fact['focus']):

            if isinstance(focus['value'], int) or isinstance(focus['value'], float) or isinstance(focus['value'], np.int64) or isinstance(focus['value'], np.float64) or isinstance(focus['value'], np.bool_):
                fact['focus'][i]['value'] = str(fact['focus'][i]['value'])
            elif isinstance(focus['value'], datetime.datetime) or not isinstance(focus['value'], str):
                date_text = str(focus['value'])[:10]
                date = datetime.datetime.strptime(date_text, '%Y-%m-%d')
                fact['focus'][i]['value'] = date.strftime('%Y/%m/%d')
        for i, subspace in enumerate(fact['subspace']):
            if isinstance(subspace['value'], int) or isinstance(subspace['value'], float) or isinstance(subspace['value'], np.int64) or isinstance(subspace['value'], np.float64) or isinstance(subspace['value'], np.bool_):
                fact['subspace'][i]['value'] = str(fact['subspace'][i]['value'])
            elif isinstance(subspace['value'], datetime.datetime) or not isinstance(subspace['value'], str):
                date_text = str(subspace['value'])[:10]
                date = datetime.datetime.strptime(date_text, '%Y-%m-%d')
                fact['subspace'][i]['value'] = date.strftime('%Y/%m/%d')
        return fact