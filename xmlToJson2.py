from bs4 import BeautifulSoup
from bs4.element import NavigableString


class XmlToJson(object):
    def init(self, tei):
        print("Init XmlToJson tool...")
        self.soup = BeautifulSoup(tei, 'xml')
        self.author_names = []
        self.title = ""
        self.abs = ""
        self.keywords = []
        self.bookmarks = []
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

    def _getText(self, tag):
        text = ""
        for child in tag.children:
            if (isinstance(child, NavigableString)):
                if (child == '\n'):
                    continue
                text += " " + child
            else:
                text += " " + child.text
        return text.strip()


    def dealBody(self):
        s_body = self.soup.find(name='body')
        # s_body = self.soup.find(name='text')
        divs = s_body.find_all('div')
        key0 = {}.keys()
        cnt = 3

        for i, div in enumerate(divs):

            if ('xmlns:' not in div.attrs.keys()):
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
                            for child in div.children:
                                if (isinstance(child, NavigableString)
                                        and child == '\n'):
                                    continue
                                _dtext.append(self._getText(child))
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
            for child in div.children:
                if (isinstance(child, NavigableString) and child == '\n'):
                    continue

                if child.name == 'head':
                    continue
                dtext.append(self._getText(child))

            self.bookmarks.append(dtitle)
            self.papertext.append(dtext)

    def dealBack(self):
        s_back = self.soup.find(name='back')
        # ref
        ref_div = s_back.find('div', attrs={'type': 'references'})
        refs = ref_div.find_all('biblStruct')

        for ref in refs:
            ref_item = {}

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
            'References': self.ref_list
        }

        return self.data