from bs4 import BeautifulSoup
from bs4.element import NavigableString
import json
import string

class XmlToJson(object):
    def init(self, tei):
        #print("Init XmlToJson tool...")
        self.soup = BeautifulSoup(tei, 'xml')
        self.author_names = []
        self.title = ""
        self.abs = ""
        self.keywords = []
        self.bookmarks = []
        self.tables = []
        self.figures = []
        self.papertext = []
        self.ref_list = []
        self.data = None

    def dealHeader(self):
        s_header = self.soup.find(name='teiHeader')

        # title
        self.title = s_header.find_all(name='title', level='a', type='main')[0].text.strip().lower()
        
        # abs
        self.abs = s_header.find(name='abstract').text.strip()
        
        #author
        authors = s_header.find_all(name='author')
        for author in authors:
            fname = author.find('forename')
            if (fname):
                name = fname.text.strip()
            else:
                name = ""

            sname = author.find('surname')
            if (sname):
                name += " " + sname.text.strip()
            else:
                pass

            if (name != ""):
                self.author_names.append(name)

    def _dealFormula(self,tag):
        if("xml:id" in tag.attrs.keys()):
            fid_str = tag.attrs['xml:id']
            return "<" + fid_str + ">" #<formula_0>
        else:
            return "<formula>"
    
    def _dealRef(self,tag):
        if('type' in tag.attrs.keys()):
            rtype = tag.attrs['type']
            
            rid = ""
            if('target' in tag.attrs.keys()):
                rid = tag.attrs['target'] #b13 tab_0 fig_0
            
            if(rid != ""):
                rid_str = " id=" + rid
            else:
                rid_str = ""

            rtext = tag.text

            if(rtype == 'bibr'):
                return rtext + "<ref" + rid_str + ">" # (Nagai 2002) <ref id=b13>
            elif(rtype == 'table'):
                return rtext + "<table" + rid_str + ">"
            elif(rtype == 'figure'):
                return rtext + "<figure" + rid_str + ">"
            else:
                return rtext + "<" + rtype + rid_str + ">"
        else:
            rtext = tag.text
            if(rtext == ""):
                return "<ref>"
            else:
                return rtext + "<ref>"


    def _getText(self, tag, ptext):
        text = ""
        if(ptext != ""):
            text = ptext
        else:
            text = ""
        
        for child in tag.children:
            if (isinstance(child, NavigableString)):
                if (child == '\n'):
                    continue
                #text += " " + child
                if (child[0] in string.punctuation):
                    text = text.strip() + child.strip()
                else:
                    text = text.strip() + " " + child.strip()
            else:
                if(child.name == 'formula'):
                    #text += " " + self._dealFormula(child)
                    text = text.strip() + " " + self._dealFormula(child)
                elif(child.name == 'ref'): #type=bibr/table/figure
                    #text += " " + self._dealRef(child)
                    text = text.strip() + " " + self._dealRef(child)
                else:
                    #text += " " + child.text
                    child_text = child.text
                    if (child_text[0] in string.punctuation):
                        text = text.strip() + child_text.strip()
                    else:
                        text = text.strip() + " " + child_text.strip()
        
        return text.strip()


    def dealBody(self):
        s_body = self.soup.find(name='body')
        # s_body = self.soup.find(name='text')
        divs = s_body.find_all('div')
        figs = s_body.find_all('figure')
        key0 = {}.keys()
        cnt = 3
        whitespace = ['\n',' ']

        for i, div in enumerate(divs):

            if ('xmlns' not in div.attrs.keys()):
                continue

            dhead = div.find('head')
            dtitle = ""

            if (dhead):
                if (key0 != {}.keys()):
                    if (dhead.attrs.keys() == key0):
                        pass
                    else:
                        flag = False

                        for div_nextchild in divs[i + 1:i + cnt + 1]:
                            div_nextchild_head = div_nextchild.find('head')
                            if (div_nextchild_head):
                                if (div_nextchild_head.attrs.keys() == key0):
                                    flag = True
                                    break
                        # print(flag)
                        # print(div)
                        if (flag):
                            # append the text to precious p
                            _dtext = []
                            _ptext = ""
                            for child in div.children:
                                if (isinstance(child, NavigableString) and child in whitespace):
                                    continue

                                if child.name == 'head':
                                    continue
                                
                                if(child.name == 'formula'):
                                    #_ptext += self._dealFormula(child)
                                    _dtext.append(self._dealFormula(child))
                                elif(child.name == 'ref'):
                                    _ptext += self._dealRef(child)
                                    #dtext.append(self._dealRef(child))
                                else:
                                    #p
                                    _dtext.append(self._getText(child,_ptext))
                                    _ptext = ""
                            self.papertext[-1] += _dtext
                            continue

                        else:
                            break

                elif (dhead.attrs.keys() != {}.keys()):
                    key0 = dhead.attrs.keys()

                if ('n' in dhead.attrs.keys()):
                    dtitle += dhead.attrs['n']
                if (dtitle != ""):
                    dtitle += " "
                dtitle += dhead.text
            else:
                continue
                # dtitle = ""

            if ('appendix' in dtitle.lower()):
                continue

            if ('reference' in dtitle.lower()):
                continue

            dtext = []
            ptext = ""
            for child in div.children:
                if (isinstance(child, NavigableString) and child in whitespace):
                    continue

                if child.name == 'head':
                    continue
                
                if(child.name == 'formula'):
                    #ptext += self._dealFormula(child)
                    dtext.append(self._dealFormula(child))
                elif(child.name == 'ref'):
                    ptext += self._dealRef(child)
                    #dtext.append(self._dealRef(child))
                else:
                    #p
                    dtext.append(self._getText(child,ptext))
                    ptext = ""

            self.bookmarks.append(dtitle)
            self.papertext.append(dtext)

        for fig in figs:
            #id
            fid = ""
            if("xml:id" in fig.attrs.keys()):
                fid = fig.attrs['xml:id']

            head = ""
            fhead = fig.find("head")
            if(fhead):
                head = fhead.text.strip()
            
            label = ""
            flabel = fig.find("label")
            if(flabel):
                label = flabel.text.strip()
            
            desc = ""
            fdesc = fig.find("figDesc")
            if(fdesc):
                desc = fdesc.text.strip()

            fdata = {
                "id": fid,
                "Head" : head,
                "Label" : label,
                "Description" : desc
            }

            if("type" in fig.attrs.keys()):
                if(fig.attrs['type'] == 'table'):
                    self.tables.append(fdata)
            else:
                self.figures.append(fdata)

    def dealBack(self):
        s_back = self.soup.find(name='back')
        # ref
        ref_div = s_back.find('div', attrs={'type': 'references'})
        refs = ref_div.find_all('biblStruct')

        for ref in refs:
            ref_item = {}

            rid = ""
            if("xml:id" in ref.attrs.keys()):
                rid = ref.attrs['xml:id']
            ref_item['id'] = rid

            rt = ref.find('title', attrs={'level': 'a'})
            if (rt):
                ref_title = rt.text
            else:
                continue
                # ref_title = ""

            ref_item['Title'] = ref_title

            ref_authors = ref.find_all('author')
            ref_author_names = []

            for rauthor in ref_authors:
                fname = rauthor.find('forename')
                if (fname):
                    name = fname.text.strip()
                else:
                    name = ""

                sname = rauthor.find('surname')
                if (sname):
                    name += " " + sname.text.strip()
                else:
                    pass
                
                if (name != ""):
                    ref_author_names.append(name)

            ref_item['Authors'] = ref_author_names

            rj = ref.find('title', attrs={'level': 'j'})
            if (rj):
                ref_item['Journal'] = rj.text

            self.ref_list.append(ref_item)

    def run(self, tei):
        self.init(tei)
        self.dealHeader()
        self.dealBody()
        self.dealBack()

        self.data = {
            'Title': self.title,
            'Authors': self.author_names,
            'Abstract': self.abs,
            'Keywords': self.keywords,
            'BookMarks': self.bookmarks,
            'Papertext': self.papertext,
            'Tables': self.tables,
            'Figures' : self.figures,
            'References': self.ref_list
        }

        return self.data


    