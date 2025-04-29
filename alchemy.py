import pandas as pd
import csv
import random

class Alchemy:
    def __init__(self, items_file, recipes_file, founditems_path):
        self.items : pd.DataFrame = pd.read_csv(items_file)
        self.recipies : pd.DataFrame = pd.read_csv(recipes_file)
        self.founditems_path = founditems_path
        self.quest1 = []
        self.quest2 = []
        self.q1len = 2
        self.q2len = 3
        self.baseitems = ["물", "불", "흙", "공기"]
        
        #dictionary of item name : userid
        with open(founditems_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            self.founditems = {row[0]: int(row[1]) for row in reader}
        
        self.usable_items = {}
        for item in self.founditems.keys():
            cnt = self.craftable_cnt(item)
            if cnt > 0:
                self.usable_items[item] = cnt

        imm = self.immediate_craftables()
        far = self.faraway_craftables()
        if len(imm) > 0:
            self.quest1 = random.sample(imm, min(self.q1len, len(imm)))
        if len(far) > 0:
            self.quest2 = random.sample(far, min(self.q2len, len(far)))

    def immediate_craftables(self):
        temp= self.recipies['result'][self.recipies['ing1'].isin(self.founditems) & self.recipies['ing2'].isin(self.founditems)].unique()
        return [item for item in temp if item not in self.founditems]

    def faraway_craftables(self):
        temp = self.recipies['result'][self.recipies['ing1'].isin(self.founditems) & self.recipies['ing2'].isin(self.founditems)].unique()
        return [item for item in self.items['name'].values if item not in temp and item not in self.baseitems]

    def craftable_cnt(self, item):
        return sum(1 for item in self.craftable_items(item) if item not in self.founditems)

    def val_item(self, item):
        return item in self.items['name'].values
    
    def get_emoji(self, item):
        return self.items.loc[self.items['name'] == item, 'emoji'].values[0]

    def combine(self, ing1, ing2):
        result = self.recipies['result'][(self.recipies['ing1'] == ing1) & (self.recipies['ing2'] == ing2)].to_list()
        result.extend(self.recipies['result'][(self.recipies['ing1'] == ing2) & (self.recipies['ing2'] == ing1)].values)
        if len(result) == 0:
            return []
        return result
    
    def get_possible_ings(self, item):
        temp = self.recipies[self.recipies["result"] == item]
        return pd.concat([temp["ing1"], temp["ing2"]], ignore_index=True).drop_duplicates().values
    
    def craftable_items(self, item):
        return self.recipies['result'][(self.recipies['ing1'] == item) | (self.recipies['ing2'] == item)].unique().tolist()
    
    def process_newitem(self, found, id):
        self.founditems[found] = id
        cnt = self.craftable_cnt(found)
        if cnt > 0:
            self.usable_items[found] = cnt
        
        for ing in self.get_possible_ings(found):
            if ing in self.usable_items:
                self.usable_items[ing] -= 1
                if self.usable_items[ing] == 0:
                    del self.usable_items[ing]
        with open(self.founditems_path, "a") as f:
            f.write(f"{found}, {id}\n")
        
        if found in self.quest1:
            self.quest1.remove(found)
            imm = set(self.immediate_craftables()) - set(self.quest1)
            if len(imm) > 0:
                self.quest1.append(random.choice(imm))
        if found in self.quest2:
            self.quest2.remove(found)
            far = set(self.faraway_craftables()) - set(self.quest2)
            if len(far) > 0:
                self.quest2.append(random.choice(far))

    def known_recipes(self, item):
        recipes = self.recipies[self.recipies["result"] == item]
        return [(row.ing1, row.ing2) for row in recipes.itertuples() if row.ing1 in self.founditems and row.ing2 in self.founditems]