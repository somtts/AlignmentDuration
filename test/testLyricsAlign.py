'''
Created on Jan 13, 2016

@author: joro
'''
import os
import sys
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from align.LyricsAlign import alignRecording

def testLyricsAlign():
    
    currDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) )

    symbtrtxtURI = os.path.join( currDir, '../example/nihavent--sarki--aksak--gel_guzelim--faiz_kapanci/nihavent--sarki--aksak--gel_guzelim--faiz_kapanci.txt')
    sectionMetadataURI =  os.path.join( currDir, '../example/nihavent--sarki--aksak--gel_guzelim--faiz_kapanci/nihavent--sarki--aksak--gel_guzelim--faiz_kapanci.sectionsMetadata.json' )
    sectionLinksURI =   os.path.join( currDir, '../example/nihavent--sarki--aksak--gel_guzelim--faiz_kapanci/18_Munir_Nurettin_Selcuk_-_Gel_Guzelim_Camlicaya/18_Munir_Nurettin_Selcuk_-_Gel_Guzelim_Camlicaya.sectionLinks.json' )
    audioFileURI =  os.path.join( currDir, '../example/nihavent--sarki--aksak--gel_guzelim--faiz_kapanci/18_Munir_Nurettin_Selcuk_-_Gel_Guzelim_Camlicaya/18_Munir_Nurettin_Selcuk_-_Gel_Guzelim_Camlicaya.wav')
    outputDir =  os.path.join( currDir, '../example/output/' )
    
    extractedPitch = os.path.splitext(audioFileURI)[0] + '.pitch'
    with open(extractedPitch) as f:
        extractedPitchList = json.load(f)
    
    totalDetectedTokenList = alignRecording(symbtrtxtURI, sectionMetadataURI, sectionLinksURI, audioFileURI, extractedPitchList, outputDir)
    ret = {'alignedLyricsSyllables':{} }
    ret['alignedLyricsSyllables'] =   totalDetectedTokenList
    print ret



if __name__ == '__main__':
    testLyricsAlign()