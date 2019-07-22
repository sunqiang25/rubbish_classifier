import os,codecs,collections
import ahocorasick
from itertools import chain
from py2neo import Graph,Node
class QuestionClassifier:
    def __init__(self):
        #self.ask_rubbish_category = ["是什么","属于什么"]
        #self.identified_rubbish_category = ["还是"]
        #self.rubbish_category_contain = ["哪些"]
        #self.rubbish_category_desc = ["什么"]        
        self.cur_dir = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        self.rubbish_path = os.path.join(self.cur_dir, 'rubbish.csv')
        self.rubbish_category_path = os.path.join(self.cur_dir, 'rubbish_category.csv')
        self.rubbish = [i.split(',')[1].strip() for i in codecs.open(self.rubbish_path,"r","utf-8") if i.strip()]
        self.rubbish_category = [i.split(',')[1].strip() for i in codecs.open(self.rubbish_category_path,"r","utf-8") if i.strip()]
        self.rubbish_related = set(self.rubbish+self.rubbish_category)
        self.rubbish_actree = self.build_rubbish_actree(list(self.rubbish_related))
        self.rubbish_wdtype_dict = self.build_rubbish_wdtype_dict()
        self.g = Graph(
            host="127.0.0.1",
            port="7687",
            bolt = True,
            user="neo4j",
            password="1qaz@WSX")            
        #self.g = Graph(
            #host="10.37.2.247",
            #http_port=7474,
            #user="neo4j",
            #password="1qaz@WSX")        

    def build_rubbish_actree(self, wordlist):
        """add the words to the trietree"""
        actree = ahocorasick.Automaton()
        for index, word in enumerate(wordlist):
            actree.add_word(word, (index, word))
        actree.make_automaton()
        return actree    
        
    def check_rubbish(self, question):
        """find question from trietree"""
        rubbish_wds = []
        for i in self.rubbish_actree.iter(question):
            wd = i[1][1]
            rubbish_wds.append(wd)
        stop_wds = []
        for wd1 in rubbish_wds:
            for wd2 in rubbish_wds:
                if wd1 in wd2 and wd1 != wd2:
                    stop_wds.append(wd1)
        final_wds = [i for i in rubbish_wds if i not in stop_wds]
        #final_wds = set(rubbish_wds)
        final_dict_ = collections.defaultdict(str)
        for i in final_wds:
            types = self.rubbish_wdtype_dict.get(i)
            for type in types:
                if type not in final_dict_:
                    final_dict_[type]=[i]
                else:
                    final_dict_[type].append(i)
        #final_dict = {i:self.rubbish_wdtype_dict.get(i) for i in final_wds}

        return final_dict_
    
    def build_rubbish_wdtype_dict(self):
        """build the classifier , like the NER"""
        wd_dict = dict()
        for wd in self.rubbish_related:
            wd_dict[wd] = []
            if wd in self.rubbish:
                wd_dict[wd].append('rubbish')
            if wd in self.rubbish_category:
                wd_dict[wd].append('rubbish_category')
        return wd_dict
    
    #def check_keywords(self, keywords, question):
        #for keyword in keywords:
            #if keyword in question:
                #return True
        #return False  
    
    def classify(self, question):
        
        data = {}
        rubbish_dict = self.check_rubbish(question)
        if not rubbish_dict:
            return {}
        types =rubbish_dict.keys()
        question_type = 'others'
        types_wd = "".join(chain(*rubbish_dict.values()))
        entities = list(set(chain(*rubbish_dict.values())))
        #if types_wd==question or (self.check_keywords(self.ask_rubbish_category, question) and "rubbish" in types):
        if len(set(types)) ==1:
            if "rubbish" in types:
                question_type = "ask_rubbish_category"
            else:
                question_type = "rubbish_category_desc"             
        else:
            question_type = "identified_rubbish_category"
            entities = list(rubbish_dict.values())[0]
        queries = self.query_transfer(question_type, entities)
        answer = "垃圾分类机器人小强为您服务"
        result = []
        for query in queries:
            try:
                #result.append(self.g.run(query).evaluate()) #evaluate() replace data()
                result +=self.g.run(query).data()
            except Exception as e:
                print(e)
        answer = self.pretty_answer(question_type, result)
        return answer
    def pretty_answer(self,question_type,answers):
        final_answer = []
        if not answers:
            return ''
        if question_type == "ask_rubbish_category":
            for i in answers:
                final_answer.append("{0}是{1}".format(i['m.name'],i['r.name']))
        if question_type == "rubbish_category_desc":
            final_answer.append(answers[0]["m.desc"])
            example=[]
            for i in answers[1:]:
                example.append(i["m.name"])
            final_answer.append(example)
        if question_type == "identified_rubbish_category":
            for i in answers:
                final_answer.append("{0}是{1}".format(i['m.name'],i['r.name']))
        return final_answer

    def query_transfer(self, question_type, entities):
        if not entities:
            return []
        query = []
        if question_type == 'ask_rubbish_category':
            query = ["match (m:rubbish)-[r]->(n:rubbish_category) where m.name='{0}' return r.name,m.name".format(i) for i in entities]
        if question_type == "rubbish_category_desc":
            query = ["match (m:rubbish_category) where m.name='{0}' return m.desc,m.name".format(i) for i in entities]+["MATCH (m:rubbish)-[r]->(n:rubbish_category) where n.name='{0}' RETURN m.name,n.name LIMIT 25".format(i) for i in entities]
        if question_type == "identified_rubbish_category":
            query = ["match (m:rubbish)-[r]->(n:rubbish_category) where m.name='{0}' return r.name,m.name".format(i) for i in entities]
        return query
            
if __name__ == '__main__':
    handler = QuestionClassifier()
    while 1:
        question = input('input an question:')
        answer = handler.classify(question)
        if answer:
            print(answer)
        else:
            print( "垃圾分类机器人小强还在学习中...")