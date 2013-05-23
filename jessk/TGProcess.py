##########
#TGProcess.py
#Version 1.0.1
##########

import re
import operator
import csv

"""Conventions:
This script zero-indexes everything. So, the first point/interval in the first tier is
referenced as textGrid[0][0].

Also, Praat strangely decided to call tiers "items."  I ignore this convention, and
instead use "item" as the general term for a Point or an Interval.  I have not (yet)
found a need to superclass Point and Interval, but if I did, I'd have it be Item, and
define Point(Item) and Interval(Item)
"""

def stripQuotes(s):
    """Removes outer quotes, and whitespace outside those quotes, from a mark/text."""
    """ stripQuotes(" \"This is the intended use\"  ") yields "This is the intended use"  """
    """ stripQuotes(" \"This is the \"intended\" use  ") yields "This is the \"intended\" use" """
    return s[::-1].strip().replace('"',"",1)[::-1].replace('"',"",1)

class TextGrid:
    """Top-level object for storing and manipulating TextGrids."""
    def __str__(self):
        return "TextGrid with " + str(len(self)) + " tiers: " + ", ".join(["\"" + tier.name + "\"" for tier in self.tiers])
    __repr__ = __str__
    def __len__(self):
        return len(self.tiers)
    def __getitem__(self,i): #allows textGrid[i] where textGrid = TextGrid()
        if isinstance(i,int):
            return self.tiers[i]
        elif isinstance(i,str):
            l = [x for x in range(0,len(self.tiers)) if self.tiers[x].name==i]
            if len(l) == 1:
                return self.tiers[l[0]]
            else:
                raise Exception("There are " + len(l) + " tiers with name " + i)
        else:
            raise TypeError("Expecting int or str, got " + type(i))
    def __setitem__(self,i,item):
        #TODO:  implement name-based accessing.
        self.tiers[i]=item
    def __delitem__(self,i):
        #TODO:  implement name-based accessing.
        del(self.tiers[i])
    def append(self,item):
        self.tiers.append(item)
    def __init__(self,fileType="ooTextFile",objectClass="TextGrid",xmin="0 ",xmax="",hasTiers="exists",filepath=None):
        """Creates an empty TextGrid with to specified metadata, or reads a grid from the filepath into a new TextGrid instance."""
        if filepath != None:
            self.tiers = []
            self.readGridFromPath(filepath)
        else:
            self.tiers = []
            self.fileType = fileType
            self.objectClass = objectClass
            self.xmin = xmin
            self.xmax = xmax
            self.hasTiers = hasTiers
            self.enc = None #Encoding must be set when grid is read.
                            #We don't define self.size.  We simply use len(self.tiers)
        
    def writeGridToPath(self, path):
        """Writes the TextGrid in the standard TextGrid format to the file path."""
        f = open(path,'w',encoding=self.enc)
        self.writeGrid(f)
        
    def writeGrid(self,f):
        f.write("File type = \"" + self.fileType + "\"\n")
        f.write("Object class = \"" + self.objectClass + "\"\n")
        f.write("\n")
        f.write("xmin = " + self.xmin + "\n")
        f.write("xmax = " + self.xmax + "\n")
        f.write("tiers? <" + self.hasTiers + "> \n")
        f.write("size = " + str(len(self.tiers)) + " \n")
        f.write("item []: \n")
        for tierNum in range(0,len(self.tiers)):
            f.write("    item [" + str(tierNum+1) + "]:\n")
            self.tiers[tierNum].writeTier(f)

    def readGridFromPath(self, filepath):
        """Parses a .TextGrid file and represents it internally in this TextTier() instance."""
        try:
            self.readGrid(open(filepath,'r',encoding='utf-8'))
        except UnicodeDecodeError:
            self.readGrid(open(filepath,'r',encoding='utf-16'))
 
    def readGrid(self,f):
        """Parses the .TextGrid file described by the file descriptor and represents it internally in this TextTier() instance.  It is recommended to use readGridFromPath() unless you have a good reason not to."""

        #f.seek(0) #Should we do this?  Probably not.

        self.enc = f.encoding

        #Regexes for parsing info from TextGrid
        fileTypeRE = re.compile(r"File type = \"(.+)\"")
        objectClassRE = re.compile(r"Object class = \"(.+)\"")
        xminRE = re.compile(r"xmin = (.+)")
        xmaxRE = re.compile(r"xmax = (.+)")
        tiersRE = re.compile(r"tiers\? <(.+)>")
        sizeRE = re.compile(r"size = (.+)")
        
        tierRE = re.compile(r"item \[(.+)\]:") # beginning of new tier!
        classRE = re.compile("class = \"(.+)\"")
        nameRE = re.compile(r"name = \"(.+)\"")

        pointOrIntervalRE = re.compile(r"(points|intervals) \[(.+)\]:")
        #Note, pointOrIntervalRE has TWO backreferences. At present, only the first is used.

        timeRE = re.compile(r"(?:number|time) = (.+)") 
        markRE = re.compile(r"mark = (.+)")
        textRE = re.compile(r"text = (.+)")

        inMeta = True #reading the Grid metadata section, not the data tiers.
        line = True #starts off the while loop
        while line:
            line = f.readline() #line needs to be read in front. This is clunky.  Sol'n?
            if not line:
                break
            
            if inMeta:
                match = fileTypeRE.search(line)
                if match:
                    self.fileType = match.groups()[0]
                    continue

                match = objectClassRE.search(line)
                if match:
                    self.objectClass = match.groups()[0]
                    continue

                match = xminRE.search(line)
                if match:
                    self.xmin = match.groups()[0]
                    continue

                match = xmaxRE.search(line)
                if match:
                    self.xmax = match.groups()[0]
                    continue

                match = tiersRE.search(line)
                if match:
                    self.hasTiers = match.groups()[0]
                    continue

                #Currently, we dierctly tabulate "size" from the data.
                """match = sizeRE.search(line)
                if match:
                    self.size = match.groups()[0]
                    continue"""

                match = tierRE.search(line)
                if match:
                    inMeta = False
                    #"Don't interpret future lines as grid metadata..."
                    self.tiers.append(Tier())
                    inTierMeta = True
                    #"...they are tier metadata (or point/interval data)"
                    continue
                
            elif inTierMeta:
                #All upcoming [-1]'s indicate that the lines pertain to the most recently \
                # added tier.
                match = classRE.search(line)
                if match:
                    self[-1].tierClass = match.groups()[0]
                    continue

                match = nameRE.search(line)
                if match:
                    self[-1].name = match.groups()[0]
                    continue

                match = xminRE.search(line)
                if match:
                    self[-1].xmax = match.groups()[0]
                    continue

                match = xmaxRE.search(line)
                if match:
                    self[-1].xmax = match.groups()[0]
                    continue

                match = pointOrIntervalRE.search(line)
                if match:
                    itemType = match.groups()[0]
                    if itemType == "points":
                        self[-1].append(Point()) 
                    elif itemType =="intervals":
                        self[-1].append(Interval())
                    else:
                        raise Exception("Tier is said not to contain points nor intervals, but " + itemType)
                    inTierMeta = False #Done reading this tier's metadata.  Next lines are data.
                    continue
            else: # not in any type of metadata: this is an item
                  #TODO: factor out test for interval vs point?
                match = timeRE.search(line)
                if match:
                    self[-1][-1].time = match.groups()[0]
                    continue

                match = xminRE.search(line)
                if match:
                    self[-1][-1].xmin = match.groups()[0]
                    continue

                match = xmaxRE.search(line)
                if match:
                    self[-1][-1].xmax = match.groups()[0]
                    continue
                
                match = markRE.search(line)
                if match:
                    mark = match.groups()[0]
                    while mark.count('"')%2==1: #Praat escapes quotes by doubling: '"' -> '""'
                        #If the quotes don't add up to an even number (1 opening +  1 closing + 2*escaped quote count), \
                        #the mark must be multi-lined.
                        line = f.readline() 
                        if line:
                            mark += line
                        else:
                            raise Exception("TextGrid file ends mid-mark!")
                    if self[-1].tierClass == "TextTier":
                        self[-1][-1].mark = stripQuotes(mark)
                    else:
                        raise Exception("Found a \"mark\" in a non-TextTier.")
            
                    continue

                match = textRE.search(line)
                if match:
                    text = match.groups()[0]
                    while text.count('"')%2==1:
                        line = f.readline()
                        if line:
                            text += line
                        else:
                           raise Exception("TextGrid file ends mid-text!")
                    if self[-1].tierClass == "IntervalTier":
                        self[-1][-1].text = stripQuotes(text)
                    else:
                        raise Exception("Found a \"text\" in a non-IntervalTier!")
                    continue

                #new point or interval
                match = pointOrIntervalRE.search(line)
                if match:
                    itemType = match.groups()[0]
                    if itemType == "points":
                        self[-1].append(Point())
                    elif itemType == "intervals":
                        self[-1].append(Interval())
                    else:
                        raise Exception("Tier is said not to contain points nor intervals, but " + itemType)
                    continue

                match = tierRE.search(line)
                if match:
                    self.append(Tier())
                    inTierMeta = True #We just started a tier, we need to read the metadata.
                    continue
    def listTiers(self):
        for i in range(0,len(self)):
            print(str(i+1) + ": " + str(self[i]))
                
class Tier:
    """Object for storing and manipulating Tiers.
    Intended to be stored in a TextGrid() instance."""
    def __init__(self,tierClass="TextTier",name="",xmin="0 ",xmax="0 "):
        self.tierClass = tierClass
        self.name = name
        self.xmin = xmin
        self.xmax = xmax
        self.items = []
    def __str__(self):
        return " \"" + self.name + "\" " + self.tierClass + " with " + str(len(self.items)) + " items."
    __repr__ = __str__
    def __len__(self):
        return len(self.items)
    def __getitem__(self,i):
        return self.items[i]
    def __setitem__(self,i,item):
        self.items[i]=item
    def __delitem__(self,i):
        self.removeItem(i) #See below
    def append(self,item):
        self.items.append(item)
    def sort(self, *args, **kwords):
        self.items.sort(*args,**kwords)
    def writeTier(self,f):
        """Writes the contents of the Tier to the file f in TextGrid format.
        Intended to be called as part of TextGrid().writeGrid(), as to contribute to a valid TextGrid file."""
        f.write("        class = \"" + self.tierClass + "\" \n")
        f.write("        name = \"" + self.name + "\" \n")
        f.write("        xmin = " + self.xmin + "\n")
        f.write("        xmax = " + self.xmax + "\n")
        if self.tierClass == "IntervalTier":
            f.write("        intervals: size = " + str(len(self.items)) + " \n")
            for itemNum in range(0,len(self.items)):
                f.write("        intervals [" + str(itemNum+1) + "]:\n")
                self.items[itemNum].writeInterval(f)
        elif self.tierClass == "TextTier":
            f.write("        points: size = " + str(len(self.items)) + " \n")
            for itemNum in range(0,len(self.items)):
                f.write("        points [" + str(itemNum + 1) + "]:\n")
                self.items[itemNum].writePoint(f)
        
        
    def pointFromTime(self,time):
        """Returns the first point whose time is at or after the time argument."""
        #Binary (?) search: O(log n) time.
        def recurse(firstUnchecked,firstChecked):
            #print((firstUnchecked,firstChecked))
            if firstUnchecked == firstChecked:
                return (self[firstChecked],firstUnchecked)
            toCheck = int((firstUnchecked + firstChecked)/2) #Floor of average
            currentTime = float(self[toCheck].time)
            if currentTime >= time:
                #Too high
                return recurse(firstUnchecked, toCheck)
            else:
                #Too low:
                return recurse(toCheck + 1,firstChecked)
        return recurse(0,len(self))

    def addInterval(self,interval):
        """Adds an interval to the Tier."""
        #TODO: Use log(n) algorithm to find correct placement 
        if self.items == []:
            self.items.append(interval)
            return
        addLoc = 0
        while float(self[addLoc].xmin)<float(interval.xmin):
            addLoc+=1
            if addLoc == len(self.items):
                self.items.append(interval)
                return
            
    def addPoint(self,point): #TODO: Use log(n) algorithm to find correct placement
        if self.items == []:
            self.items.append(point)
            return
        addLoc = 0
        while float(self[addLoc].time)<float(point.time):
            addLoc+=1
            if addLoc == len(self.items):
                self.items.append(point)
                return
            
        if self[addLoc].time.strip() == point.time.strip():
            # Merge
            self[addLoc].mark = self[addLoc].mark + "/" + point.mark
        else: 
            self.items.insert(addLoc,point)
 
    def addSameTimePoints(self, points, dt_max=.001):
        """Adds a list of points, all with the same time (the "requested time"), to the tier."""
        #TODO: Check that all points have the same time?
        requested_time = points[0].time
        if self.items == []:
            first_time = float(requested_time)
            dt = dt_max
        else:
            add_loc = 0
            while float(self[add_loc].time) <= float(requested_time):
                add_loc += 1
                if add_loc == len(self.items):
                    #the requested time is after *every* other point
                    first_time = float(requested_time)
                    dt = dt_max
                    break
            else:
                #self[add_loc].time is after requested_time.
                #We wish to squeeze the points before that.
                if add_loc == 0:
                    first_time = float(requested_time)
                    dt = min((float(self[add_loc].time) - float(requested_time))/len(points), dt_max)
                elif self[add_loc-1].time == requested_time:
                    dt = min((float(self[add_loc].time) - float(requested_time)
                          )/(len(points)+1), dt_max);
                    first_time = float(requested_time) + dt
                else:
                    first_time = float(requested_time)
                    dt = min((float(self[add_loc].time) - float(requested_time))/len(points), dt_max)
            for number, point in enumerate(points):
                moved_point = Point(str(first_time + number*dt), point.mark)
                self.items.insert(add_loc + number, moved_point)
       
    def removeItem(self,itemIndex):
        del(self.items[itemIndex])

    ##Aliases:##
    def removePoint(self,pointIndex):
        self.removeItem(pointIndex)

    def removeInterval(self,intervalIndex):
        self.removeItem(intervalIndex)
    ##End Aliases.##
        
    def writeTierToPathAsCSV(self,filepath):
        """Writes the contents of a tier to a path as a CSV (Excel-readable) file."""
        tierWriter = csv.writer(open(filepath,'w',newline=''))
        if self.tierClass == "TextTier":
            tierWriter.writerow(['time','mark'])
            for point in self:
                tierWriter.writerow([point.time,point.mark])
        elif self.tierClass == "IntervalTier":
            tierWriter.writerow(['xmin','xmax','text'])
            for interval in self:
                tierWriter.writerow([interval.xmin,interval.xmax,interval.text])

    def removeBlankPoints(self):
        """Removes all points whose mark is an empty string"""
        i = 0
        while i < len(self.items):
            if type(self.items[i]) == Point and self.items[i].mark == "":
                self.removeItem(i)
            else:
                i+=1
    
class Interval:
    def __init__(self,xmin = "", xmax = "", text = ""):
        self.xmin = xmin
        self.xmax = xmax
        self.text = text
    def __str__(self):
        return "(" + self.xmin + "," + self.xmax +") " + self.text
    __repr__ = __str__
    def writeInterval(self, f):
        f.write("            xmin = " + self.xmin + "\n")
        f.write("            xmax = " + self.xmax + "\n")
        f.write("            text = \"" + self.text + "\" \n")


class Point:
    def __init__(self,time = "", mark=""):
        self.time = time
        self.mark = mark
    def __str__(self):
        return self.time + " " + self.mark
    __repr__ = __str__
    #This __lt__ function is definend only for sorting purposes.
    #If we wish to expand for __gt__, __eq__, etc, we'll need to devote some thought to it,
    #because we may only want to consider points "equal" if their times *and* marks are the same.
    def __lt__(self,other):
        try:
            return operator.lt(float(self.time),float(other.time))
        except:
            try:
                return operator.lt(float(self.time),float(other))
            except:
                raise TypeError("Unorderable types: Point() < " + type(other))
            
    def landmarkList(self):
        """Separates the mark's string of slash-separated landmarks into a list of single landmarks."""
        return self.mark.split("/")
    def setMarkFromList(self,list):
        """Takes a list of landmarks, joins them with slashes, and sets the resulting string as the point's mark."""
        self.mark = "/".join(list)

    
    def writePoint(self,f):
        f.write("            number = " + self.time + "\n")
        f.write("            mark = \"" + self.mark + "\" \n")
    
