
# Copyright 2015,2016 Music Technology Group - Universitat Pompeu Fabra
#
# This file is part of Dunya
#
# Dunya is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation (FSF), either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/

# Lyrics-to-audio alignment with syllable duration modeling
""" please cite:
Dzhambazov, G., & Serra X. (2015).  Modeling of Phoneme Durations for Alignment between Polyphonic Audio and Lyrics.
Sound and Music Computing Conference 2015.
"""

from align.FeatureExtractor import FeatureExtractor
import os
import sys
import json
import subprocess
from for_makam.MakamRecording import parseSectionLinks, MakamRecording
from align.Decoder import logger,  Decoder
from ParametersAlgo import ParametersAlgo
from parse.TextGrid_Parsing import tierAliases
parentDir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__) ), os.path.pardir, os.path.pardir)) 



import essentia.standard

projDir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__) ), os.path.pardir )) 

modelDIR = projDir + '/models_makam/'
HMM_LIST_URI = modelDIR + '/monophones0'
MODEL_URI = modelDIR + '/hmmdefs9gmm9iter'

from for_makam.MakamScore import  loadMakamScore2


from utilsLyrics.Utilz import writeListOfListToTextFile, writeListToTextFile,\
    getMeanAndStDevError, getSectionNumberFromName, readListOfListTextFile, \
    readListTextFile, getMelodicStructFromName, addTimeShift,  fetchFileFromURL

from htkparser.htk_converter import HtkConverter
ANNOTATION_EXT = '.TextGrid'
 
  


class LyricsAligner():
    def __init__(self, recording,  WITH_SECTION_ANNOTATIONS, path_to_hcopy):
        
        self.recording = recording
        self.WITH_SECTION_ANNOTATIONS = WITH_SECTION_ANNOTATIONS
        self.path_to_hcopy = path_to_hcopy
        self.tokenLevelAlignedSuffix = determineSuffix(ParametersAlgo.WITH_DURATIONS, ParametersAlgo.WITH_ORACLE_PHONEMES, ParametersAlgo.WITH_ORACLE_ONSETS, ParametersAlgo.DETECTION_TOKEN_LEVEL)
        
        if ParametersAlgo.FOR_MAKAM:
            
        
            self.model = HtkConverter()
            self.model.load(MODEL_URI, HMM_LIST_URI)
        
        elif ParametersAlgo.FOR_JINGJU:
            #### read models_makam done in LyricsWithModels depending 
            self.model = self.recording.which_fold
        else: 
            sys.exit('neither JINGJU nor MAKAM.')



    def alignRecording(self, extractedPitchList, outputDir ):
            '''
            each section link has 
            '''
            # parameters 
            if self.WITH_SECTION_ANNOTATIONS: 
                sectionLinks = self.recording.sectionAnnos
            else:
                sectionLinks = self.recording.sectionLinks

                
            detectedSectionList = []    
            for  currSectionLink in sectionLinks :
                    
                    detectedTokenList = []
#                     if sectionLink.melodicStructure.startswith('ARANAGME'):
#                         print("skipping sectionLink {} with no lyrics ...".format(sectionLink.melodicStructure))
#                         continue                
                    if not hasattr(currSectionLink, 'section') or currSectionLink.section == None:
                        print("skipping sectionAnno {} not matched to any score section ...".format(currSectionLink))
                        continue   
                    
                    
                    if self.WITH_SECTION_ANNOTATIONS: 
                        lyrics = currSectionLink.section.lyrics
             
                        lyricsStr = lyrics.__str__()
                        if not lyricsStr or lyricsStr=='None' or  lyricsStr =='_SAZ_':
                            print("skipping sectionLink {} with no lyrics ...".format(currSectionLink.melodicStructure))
                            continue 
                        detectedTokenList, detectedPath, maxPhiScore = self.alignLyricsSection(  extractedPitchList,   [],  self.tokenLevelAlignedSuffix,   currSectionLink)
#                         self.extractNoteOnsetsAndEval(currSectionLink)
      
                     
                    else:  # section links
                        detectedTokenList = self.alignSectionLinkProbableSections( extractedPitchList, currSectionLink)
                    
                    currSectionLink.detectedTokenList = detectedTokenList 
                    detectedSectionList.append(currSectionLink.detectedTokenList)
        
            return detectedSectionList, self.recording.sectionLinksOrAnnoDict          
                     
             
    def evalAccuracy(self):
        
        pathEvaluation = os.path.join(parentDir, 'AlignmentEvaluation')
        if pathEvaluation not in sys.path:
                    sys.path.append(pathEvaluation)
        from align_eval.AccuracyEvaluator import _evalAccuracy
                        
        totalCorrectDurations = 0
        totalDurations = 0    
        
        if self.WITH_SECTION_ANNOTATIONS: 
                sectionLinks = self.recording.sectionAnnos
        else:
                sectionLinks = self.recording.sectionLinks
                
        for currSectionLink in sectionLinks:
          #                 break
                        correctDuration = 0
                        totalDuration = 1
                        
               
                        evalLevel = tierAliases.pinyin
                        URIRecordingChunkTextGrid = currSectionLink.URIRecordingChunk + ANNOTATION_EXT
                        if ParametersAlgo.FOR_JINGJU:
                            audioName = os.path.basename(self.recording.recordingNoExtURI)
                            path_TextGrid =  os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(self.recording.recordingNoExtURI) ), os.path.pardir, os.path.pardir)) 

                            URI_TextGrid = os.path.join(path_TextGrid, audioName + ANNOTATION_EXT)
                            
                            correctDuration, totalDuration = _evalAccuracy(URI_TextGrid, currSectionLink.detectedTokenList, evalLevel, currSectionLink.section.fromSyllableIdx, currSectionLink.section.toSyllableIdx  )
            
                        totalCorrectDurations += correctDuration
                        totalDurations += totalDuration
            
        accuracy = totalCorrectDurations / totalDurations
        logger.info("accuracy: {:.2f}".format(accuracy))                


    def alignSectionLinkProbableSections(self,  extractedPitchList,    currSectionLink):
        '''
        runs alignment on given audio multiple times with a list of probable sections with their corresponding lyrics
        @return detectedTokenList with best score
        @return selectedSection section with this score
        '''   
        maxPhiScore = float('-inf')
        probabaleSections = self.recording.score.getProbableSectionsForMelodicStructure(currSectionLink)
        
        for probabaleSection in probabaleSections:
            currSectionLink.section = probabaleSection
            currTokenLevelAlignedSuffix =  self.tokenLevelAlignedSuffix + '_' + probabaleSection.melodicStructure + '_' + probabaleSection.lyricStructure
            
            currDetectedTokenList, detectedPath, phiScore = self.alignLyricsSection( extractedPitchList,  [],   currTokenLevelAlignedSuffix,  currSectionLink)
            if phiScore > maxPhiScore:
                maxPhiScore = phiScore
                selectedSection = probabaleSection
                detectedTokenList = currDetectedTokenList
        
        # get sections with same lyrics as top-aligned section
        selectedSectionsSameLyrics =  self.recording.score.getSectionsSameLyrics( selectedSection, probabaleSections)
        currSectionLink.setSelectedSections(selectedSectionsSameLyrics)
        
        return detectedTokenList
         
         
               
    def extractNoteOnsetsAndEval(self, currSectionLink):
                    '''
                    only extract note onsets and eval note onset extraction
                    '''
                    URIrecOnsets = self.recording.recordingNoExtURI + '.alignedNotes.txt'
                    fe = FeatureExtractor(self.path_to_hcopy, currSectionLink) 
                    
                    gr_truth_URI = fe.onsetDetector.parseNoteOnsetsGrTruth(URIrecOnsets)
                    extractedOnsetsURI =  fe.onsetDetector.extractNoteOnsets(currSectionLink.URIRecordingChunk + '.wav')
                    
                    print "evaluateTranscriptions( '"  + gr_truth_URI  + "','"  + extractedOnsetsURI + "')"



    def  alignLyricsSection( self, extractedPitchList,  listNonVocalFragments,    tokenLevelAlignedSuffix,    currSectionLink):
            '''
            align @param: lyrics for one section
            '''
                
        #     read from file result
            URIRecordingChunkResynthesizedNoExt = currSectionLink.URIRecordingChunk
            detectedAlignedfileName = currSectionLink.URIRecordingChunk + tokenLevelAlignedSuffix
            fe = FeatureExtractor(self.path_to_hcopy, currSectionLink) 
            
            if not os.path.isfile(detectedAlignedfileName):
                
                fromTsTextGrid = -1; toTsTextGrid = -1
                
                if  ParametersAlgo.WITH_ORACLE_PHONEMES:
                    currSectionLink.loadSmallAudioFragmentOracle(self.model)
                    # featureVectors is alias for LyricsWithModelsOracle
                    fe.featureVectors = currSectionLink.lyricsWithModels 
                    
                    if ParametersAlgo.FOR_MAKAM:
                        # for kimseye etmem
                        fromTsTextGrid = 0; toTsTextGrid = 20.88

                    
                     
                else:
                #     ###### extract audio features
                         
                    fe.featureVectors = currSectionLink.loadSmallAudioFragment( fe, extractedPitchList,   self.recording.recordingNoExtURI,  self.model)
                
    #             sectionLink.lyricsWithModels.printWordsAndStates()
                alpha = 0.97
                decoder = Decoder(currSectionLink.lyricsWithModels, URIRecordingChunkResynthesizedNoExt, alpha)

            #################### decode
                

                ##### note onsets ############################
                if ParametersAlgo.WITH_ORACLE_ONSETS == 1:
                    URIrecOnsets = self.recording.recordingNoExtURI + '.alignedNotes.txt'
    
                    gr_truth_URI = fe.onsetDetector.parseNoteOnsetsGrTruth(URIrecOnsets)
                    
                elif ParametersAlgo.WITH_ORACLE_ONSETS == 0:
                    
                    extractedOnsetsURI =  fe.onsetDetector.extractNoteOnsets(URIRecordingChunkResynthesizedNoExt + '.wav')
                ###############################################
                

                detectedTokenList = decoder.decodeAudio(fe, listNonVocalFragments, False,  fromTsTextGrid, toTsTextGrid)
                detectedTokenList = addTimeShift(detectedTokenList,  currSectionLink.beginTs)
                
                
                ##### write all decoded output persistently to files
                tokenAlignedfileName = URIRecordingChunkResynthesizedNoExt + tokenLevelAlignedSuffix
                with open(tokenAlignedfileName, 'w'  ) as f1:
                    json.dump( detectedTokenList, f1)
    #             writeListOfListToTextFile(detectedTokenList, 'startTs \t endTs \t phonemeOrSyllorWord \t beginNoteNumber \n', tokenAlignedfileName)
                
                phiOptPath = {'phi': decoder.path.phiPathLikelihood}
                detectedPath = decoder.path.pathRaw
                with open(URIRecordingChunkResynthesizedNoExt + tokenLevelAlignedSuffix + '_phi', 'w'  ) as f:
                    json.dump( phiOptPath, f)
               
                
            ### VISUALIZE result 
        #         decoder.lyricsWithModels.printWordsAndStatesAndDurations(decoder.path)
            
            else:   
                    print "{}\n already exists. No decoding".format(detectedAlignedfileName)
    #                 detectedTokenList = readListOfListTextFile(detectedAlignedfileName)
                    with open(detectedAlignedfileName, 'r'  ) as f2:
                        detectedTokenList = json.load(f2)
                    
                    if ParametersAlgo.WITH_ORACLE_PHONEMES:
                        outputURI = URIRecordingChunkResynthesizedNoExt + '.path_oracle'
                    else:
                        outputURI = URIRecordingChunkResynthesizedNoExt + '.path'
                     
                    detectedPath = ''
    #                 detectedPath = readListTextFile(outputURI)
                     
                    phiOptPath = ''
    #                 with open(URIRecordingChunkResynthesizedNoExt + tokenLevelAlignedSuffix + '_phi', 'r'  ) as f:
    #                     phiOptPathJSON = json.load(f)
    #                     phiOptPath = phiOptPathJSON['phi']
                    
        
            return detectedTokenList, detectedPath, phiOptPath





def loadMakamRecording(mbRecordingID, audioFileURI, symbtrtxtURI, sectionMetadataDict, sectionLinksDict,   withAnnotations):
    '''
    refactored method
    '''
    
    makamScore = loadMakamScore2(symbtrtxtURI, sectionMetadataDict)
    makamScore.printSectionsAndLyrics()
#     raw_input("make sure lyrics are correct in sections. if not correct change URL to get file from in  get_section_metadata_dict... then press key")

    mr = MakamRecording(mbRecordingID, audioFileURI, makamScore, sectionLinksDict, withAnnotations)
    
    return mr  
    

    


   

def extendSectionLinksSelectedSections(sectionLinksDict, sectionLinksAligned):
    '''
    add selected sections as field in input sectionLinks Dict 
    @param: sectionLinksAligned - list of objects of class sectionLink with the field selectedSections set
    @return:  changed @param sectionLinksDict 
    '''
    sectionLinks = parseSectionLinks(sectionLinksDict)
    for currSectionLink in sectionLinks:
                        
                        
                        beginTimeStr = str(currSectionLink['time'][0])
                        beginTimeStr = beginTimeStr.replace("[","")
                        beginTimeStr = beginTimeStr.replace("]","")
                        
                        relevantSectionLinkAligned =  getSectionLinkBybeginTs(sectionLinksAligned, beginTimeStr)
                        
                        if not hasattr(relevantSectionLinkAligned, 'selectedSections'):
                            continue 
                        selectedSections = []
                        for currSelectedSection in relevantSectionLinkAligned.selectedSections:
                            sec = {'melodicStructure':currSelectedSection.melodicStructure, 'lyricStructure':currSelectedSection.lyricStructure}
                            selectedSections.append(sec)
                            currSectionLink['selectedSections'] = selectedSections
    return sectionLinksDict                       

def getSectionLinkBybeginTs(sectionLinks, queryBeginTs):
    for sectionLink in sectionLinks:
        if str(sectionLink.beginTs) ==  queryBeginTs:
            return sectionLink
                                 
   


    
    
    



def stereoToMono(wavFileURI):
        sampleRate = 44100
        loader = essentia.standard.MonoLoader(filename=wavFileURI, sampleRate=sampleRate)
        audio = loader()
        monoWriter = essentia.standard.MonoWriter(filename=wavFileURI)
        monoWriter(audio)
        return wavFileURI
    

def determineSuffix(withDuration, withOracle, withOracleOnsets, decodedTokenLevel):
    tokenAlignedSuffix = '.'
    tokenAlignedSuffix += decodedTokenLevel
    if ParametersAlgo.DECODE_WITH_HTK:
        tokenAlignedSuffix += '_htk_'
    else:
        if withDuration: tokenAlignedSuffix += 'Duration'
        if withOracle == 1: tokenAlignedSuffix += 'OraclePhonemes'
        elif withOracle == -1: tokenAlignedSuffix += 'NoPhonemes'
        if withOracleOnsets == 1: tokenAlignedSuffix += 'OracleOnsets'
        elif withOracleOnsets == 0: tokenAlignedSuffix += 'Onsets'
    
    tokenAlignedSuffix += 'Aligned' 
    return tokenAlignedSuffix