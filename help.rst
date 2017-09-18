.. _LIWC: liwc.net
.. _me: pboot@xs4all.nl

=======================
Some help for LIWCtools
=======================


In this document, the word *dictionary* without further qualification refers to an LIWC dictionary, not to a Python dictionary. 

Getting started
===============

Install LIWCtools using pip:

::

   pip install LIWCtools

To import LIWCtools into your script write:

::

   from LIWCtools.LIWCtools import *

Sample uses 
===========

Getting to know more about a LIWC dictionary
--------------------------------------------

Producing an HTML report about a dictionary's contents
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   LD = LDict(...dictionary filename...)
   LD.LDictHtml(...report filename...)

This will produce a report that shows the words in each of the categories. For each category it will also indicate the extrahierarchical words (see below).
If the dictionary is not stored as utf8, add an encoding parameter to LDICT. 





Comparing versions of a dictionary
----------------------------------

There are two ways of comparing dictionaries: either with or wihout a Dictionary Match Object. A straight compare between tow dictionaries can be done when the dictionaries share their category definitions. To do a comparison, execute:

::

   LDold = LDict(...filename dict 1...)
   LDnew = LDict(...filename dict 2...) 
   LDold.LDictCompare(LDnew)

The output will print the differences in terms of words that were added to or removed from the categories. A fragment may look like this:

::

    Removed words: 0 set()
    Added words: 1 {'ofzo'}
    Category with changed words: 16 adverb adverb
    Removed words: 0 set()
    Added words: 3 {'zo', 'al', 'alleen'}
    Category with changed words: 253 time time
    Removed words: 2 {'zo', 'over'}
    Added words: 0 set()
    Category with changed words: 138 incl incl
    Removed words: 4 {'bij', 'tot', 'in', 'tussen'}
    Added words: 1 {'uit'}

The second comparison generates an HTML overview of the differences between dictionaries. It uses the HTMLview method of the Dictionary Match Object. 

::

    LDM = LDictMatch(...match filename...)
    LDM.LPrint()
    LDold = LDict(...old dict filename...)
    LDnew = LDict(...new dict filename...)
    LDM.HtmlView(...report filename...,LDold,LDnew)

Generating a new LIWC dictionary
--------------------------------

The situation that this script attempts to deal with is the situation where we want to create a translation of the LIWC dictionary, while there is already a translation of an earlier version of the dictionary. The way we approached this for the Dutch translation of LIWC 2007 is that we converted the existing dictionary to the new category system, and then processed a number of change files (csv files holding the words to be added to or removed from each of the categories. 

Here is an extract of the script that generates the new dictionary. 

::

    LDold = LDict(...filename existing dict...)
    LDmodel = LDict(...model dict (the English dictionary...)
    LDMatch = LDictMatch(matchName)                             # create dictionary match object
    LDnew = LDMatch.convertDict(LDold)                          # create new dict based on straight conversion from old dict
    LDnew1 = deepcopy(LDnew)
    LDnew1.LDictUpdate(...change filename...,LDmodel)           # add or remove words from change files 
    ...
    LDnew1.LDictComplete(LDmodel)                               # complete the dictionary based on the hierarchy information
    LDnew.LDictCompare(LDnew1)                                  # compare the dictionary before and after the additions
    LDMatch.HtmlView(...report filename...)                     # compare the original and the new dictionary, based on match object
    LDnew1.LDictWrite(...output filename...)                    # write the new dictionary to disk 
    

Using a LIWC dictionary
-----------------------

Count words in LIWC categoris for a given string
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Output is a Python Counter containing frequencies of words in the categories for the dictionary in a certain string. This in effect 
replicates LIWC's main functionality as the counter can be used to create a report containing the relative frequencies.  

::

    LD = LDict(...dict filename...)
    cr = LD.LDictCountString(...string variable...)   # a Counter object

Creates a LIWC count report for a list of files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This creates an LDictCountReport object, an object that for all categories holds the words and the word counts in a list of files. 

::

    LD = LDict(...dict filename...)
    cr = LD.LDictCount(...list of text files...)   # an LDictCountReport object

Create a zipfile of the main words for each category in a set of text files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This creates a zip file that holds, for each category, the words that occur most frequently in that category, with their frequencies. This helps investigate why certain categories scores high on a body of texts.

::

    LD = LDict(...dict filename...)
    cr = LD.LDictCount(...list of text files...)				# an LDictCountReport object
    cr.write(...output filename..., ...label..., ...freq...)	# label is extra string added to names of entries in zipfile
																# freq is the relative frequency below which to stop printing (default: 0.015)







