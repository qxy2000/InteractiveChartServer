import pandas as pd
from abc import ABCMeta, abstractmethod

class IGenerator(metaclass = ABCMeta) :
    
    def __init__(self, df, scheme):
        self.df = df
        self.scheme = scheme
    
    @abstractmethod
    def generate(self, param = None):
        pass