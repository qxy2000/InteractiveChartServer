

import copy
import random
import datetime
import multiprocessing
import numpy as np

from .generator import Generator
from .fact import fact_scoring, fact_validation, fact_extraction, fact_focus

class RuleGenerator(Generator):

    def generate(self):
        print(self.scheme)
        print(self.df)

        # select an intersting topic (what is interesting? )
        # In this step we need to find out one or several relavent data columns that are interesting
        # After that, based on the selected column(s), we need to create data facts that are important
        # 
        
        # generate spatial overview

        # generate temporal overview

        # select different facts to tell the story