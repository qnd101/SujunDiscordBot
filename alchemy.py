import pandas as pd

class Alchemy:
    def __init__(self, items_file, recipes_file):
        self.items = pd.read_csv(items_file)
        self.recipies = pd.read_csv(recipes_file)

    def val_item(self, item):
        return item in self.items['name'].values
    
    def get_emoji(self, item):
        return self.items.loc[self.items['name'] == item, 'emoji'].values[0]

    def combine(self, ing1, ing2):
        result = self.recipies['result'][(self.recipies['ing1'] == ing1) & (self.recipies['ing2'] == ing2)].to_list()
        result.extend(self.recipies['result'][(self.recipies['ing1'] == ing2) & (self.recipies['ing2'] == ing1)].to_list())
        if len(result) == 0:
            return []
        return result[0].split('/')