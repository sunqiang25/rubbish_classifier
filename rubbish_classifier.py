import os,codecs,collections
import ahocorasick
from itertools import chain
from py2neo import Graph,Node
#import jieba
#from word_segment import NLP
from pyhanlp import *
from conllu import parse
import numpy as np
import random
class QuestionClassifier:
    def __init__(self):
        #self.ask_rubbish_category = ["是什么","属于什么"]
        #self.identified_rubbish_category = ["还是"]
        #self.rubbish_category_contain = ["哪些"]
        #self.rubbish_category_desc = ["什么"]    
        self.answer = [
            '我这么聪明，怎么会是垃圾呢？',
            '我就是除了尬聊什么都不会的小垃圾，唉。',
            '好了，那你又是什么垃圾？',
            '你都这样问了，我无可奉告',
            '为啥又有人问我这个问题...',
            '我还能和你聊天，看来我也不是一无是处qwq',
            '嗯？我是垃圾？嘿嘿 那你装得下我嘛？',
            '我是不可回收垃圾呜呜呜，不要卖了我',
            '我这么机智，要说是也是高智商垃圾吧'
        ]
        self.cur_dir = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        self.rubbish_path = os.path.join(self.cur_dir, 'rubbish_new.csv')
        self.rubbish_category_path = os.path.join(self.cur_dir, 'rubbish_category_new.csv')
        self.rubbish = [i.split(',')[1].strip() for i in codecs.open(self.rubbish_path,"r","utf-8") if i.strip()]
        self.rubbish_category = [i.split(',')[1].strip() for i in codecs.open(self.rubbish_category_path,"r","utf-8") if i.strip()]
        self.rubbish_related = set(self.rubbish+self.rubbish_category)
        self.rubbish_actree = self.build_rubbish_actree(list(self.rubbish_related))
        self.rubbish_wdtype_dict = self.build_rubbish_wdtype_dict()
        self.g = Graph(
            host="127.0.0.1",
            port="31423",
            bolt = True,
            user="neo4j",
            password="1qaz@WSX")            
        #self.g = Graph(
            #host="127.0.0.1",
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
        for i in self.rubbish_actree.iter(question,ignore_white_space=True):
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
    def related_question(self,segment_question):
        #l_question = jieba.lcut(question)
        #l_question = NLP().segment(question)
        related_question=[]
        for i in segment_question:
            for k in self.rubbish:
                if i in k:
                    related_question.append(k)
        return related_question        
    
    def classify(self, question):
        
        answer = []
        rubbish_dict = self.check_rubbish(question)
        if not rubbish_dict:
            trash_name = ""
            question_parseDependency = parse(str(HanLP.parseDependency(question)))
            question_Dependency= np.array([[j['form'],j['deprel']] for i in question_parseDependency for j in i])
            segment_question = list(question_Dependency[...,0])
            Dependency = list(question_Dependency[...,1])
            find_deprel = [segment_question[i] for i,v in enumerate(Dependency) if v=="主谓关系"]
            if find_deprel:trash_name = find_deprel[-1]
            if trash_name:
                answers = [
                    '{}这么聪明，怎么会是垃圾呢？'.format(trash_name),
                    '{}这么机智，要说是也是高智商垃圾吧'.format(trash_name),
                    '为啥又有人问我这个问题...',
                    '{}看起来不像来自地球，不会是太空垃圾吧？'.format(trash_name),
                    '{}这么搞笑，或许是娱乐垃圾吧'.format(trash_name)                    
                ]
                answer.append(random.choice(answers))
            related_question = self.related_question(segment_question)
            if related_question:answer.append("您也许想问的是: {}".format("//".join(related_question)))
            return answer
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
                final_answer.append("{0}属于{1}".format(i['m.name'],i['r.name']))
        if question_type == "rubbish_category_desc":
            final_answer.append(answers[0]["m.desc"])
            example=[]
            for i in answers[1:]:
                example.append(i["m.name"])
            answer = "常见的{0}有: {1}等".format(answers[0]["m.name"],"/".join(example))
            final_answer.append(answer)
        if question_type == "identified_rubbish_category":
            for i in answers:
                final_answer.append("{0}属于{1}哦".format(i['m.name'],i['r.name']))
        return final_answer

    def query_transfer(self, question_type, entities):
        if not entities:
            return []
        query = []
        if question_type == 'ask_rubbish_category':
            query = ["match (m:rubbish)-[r]->(n:rubbish_category) where m.name='{0}' return r.name,m.name".format(i) for i in entities]
        if question_type == "rubbish_category_desc":
            query = ["match (m:rubbish_category) where m.name='{0}' return m.desc,m.name".format(i) for i in entities]+["MATCH (m:rubbish)-[r]->(n:rubbish_category) where n.name='{0}' RETURN m.name,n.name LIMIT 10".format(i) for i in entities]
        if question_type == "identified_rubbish_category":
            query = ["match (m:rubbish)-[r]->(n:rubbish_category) where m.name='{0}' return r.name,m.name".format(i) for i in entities]
        return query
            
if __name__ == '__main__':
    handler = QuestionClassifier()
    while 1:
        question = input('input an question:')
        if question:
            answer = handler.classify(question)
            if answer:
                for i in answer:
                    print(i,)
            else:
                print("垃圾分类机器人小强还在学习中哦...")
        else:
            print("您还没有问我问题哦...")
