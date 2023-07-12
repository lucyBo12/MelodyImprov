import os
import random
import math
from deap import base, creator, tools, algorithms
from music21 import stream, note, chord, scale, key, meter
from midi2audio import FluidSynth
from pydub import AudioSegment
from music21 import harmony, key, roman
import simpleaudio as sa

#variables 
NUM_BARS = 4
REPEAT_COUNT = NUM_BARS // 4;
KEY = 'C'
CHORD_SEQ = ['C', 'G', 'Am', 'F'] 
ROMAN_NUMERALS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
POPULATION_SIZE = 5
GENERATIONS = 3
MUTATION_RATE = 0.3
CROSSOVER_RATE = 0.5
BEATS_PER_BAR = 8
SCALES = {'major': scale.MajorScale, 'minor': scale.MinorScale}

#creates melody based on each individual. adds melody to stream container and returns it
def create_melody(individual, key_signature, chord_seq, beats_per_bar):
    melody = stream.Stream()
    melody.append(key_signature)
    melody.append(meter.TimeSignature(f'{beats_per_bar}/4'))

    scale_notes = list(key_signature.getScale().getPitches())
    
    for i, chord_symbol in enumerate(chord_seq):
        harmony_chord = harmony.ChordSymbol(chord_symbol)
        remaining_duration = beats_per_bar
        while remaining_duration > 0:
            current_note_index = individual[i * beats_per_bar + math.floor(beats_per_bar - remaining_duration)]
            current_note_pitch = scale_notes[current_note_index % len(scale_notes)]
            duration = random.choice([0.5, 1, 1.5, 2])
            if duration > remaining_duration:
                duration = remaining_duration
            melody.append(note.Note(current_note_pitch, quarterLength=duration))
            remaining_duration -= duration

    return melody


#creates the chords for the meody from the users input. adds to stream and reurns it
def create_chords(chord_seq, key_signature, beats_per_bar):
    chords = stream.Stream()
    chords.append(key_signature)
    chords.append(meter.TimeSignature(f'{beats_per_bar}/8'))

    for chord_symbol in chord_seq:
        harmony_chord = harmony.ChordSymbol(chord_symbol)
        chord_notes = [str(pitch) for pitch in harmony_chord.pitches]
        chords.append(chord.Chord(chord_notes, quarterLength=beats_per_bar))

    return chords

#converts the midi sound file to Wav
#uses soundfont instruments to record the notes
#in this case I am using a piano sf2
def midi_to_wav(midi_file, wav_file):
    soundfont_path = 'C:/Users/recsf/lcb34MelodyImprovIser/test.sf2' #CHANGE TO PATH OF test.sf2
    fs = FluidSynth(sound_font=soundfont_path)
    fs.midi_to_audio(midi_file, wav_file)

#combines the two separte wav files containg melody and chord so they are played together
def combine_wav_files(input_files, output_file):
    combined = AudioSegment.empty()
    for file in input_files:
        segment = AudioSegment.from_wav(file)
        combined += segment
    combined.export(output_file, format="wav")

#plays the stored wav file that is specified    
def play_wav_file(filename):
    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()
    play_obj.wait_done()

#calls the functions to create the melodies and chords and converts/combines them
#asks user to evaluate
def evaluate(individual, key_signature, chord_seq, beats_per_bar):
    melody = create_melody(individual, key_signature, chord_seq, beats_per_bar)
    chords = create_chords(chord_seq, key_signature, beats_per_bar)

    midi_melody = stream.Stream([melody])
    midi_chords = stream.Stream([chords])

    midi_melody.write('midi', 'melody.mid')
    midi_chords.write('midi', 'chords.mid')

    midi_to_wav('melody.mid', 'melody.wav')
    midi_to_wav('chords.mid', 'chords.wav')
    print("\nPlease rate the following melody:")
    
    #play_wav_file('chords.wav')
    combined_stream = stream.Stream([melody, chords])
    combined_stream.write('midi', 'output.mid')

    midi_to_wav('output.mid', 'output.wav')
    play_wav_file('output.wav')
    rating = int(input("Enter rating (1-5): "))
    return 6 - rating, 

def main():
    #user input
    KEY = key.Key(str(input("Enter a key:")))
    chords_in_key = []
    for rn in ROMAN_NUMERALS:
        roman_numeral_chord = roman.RomanNumeral(rn, KEY)
        chord_root = roman_numeral_chord.root().name
        chord_quality = 'm' if roman_numeral_chord.quality == 'minor' else ''  # Add 'm' for minor chords
        chord_name = chord_root + chord_quality
        chords_in_key.append(chord_name)
    print(chords_in_key)

    chords_in_key.pop()
    print(chords_in_key)
    
    user_chords = input("Enter some of the above Chords seperated by a space ")
    CHORD_SEQ  = user_chords.split()
    #DEAP toolbox and creator to use the genetic algorithm
    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)
    toolbox = base.Toolbox()
    toolbox.register("attr_int", random.randint, 0, 7)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_int, n=NUM_BARS * BEATS_PER_BAR)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", tools.mutUniformInt, low=0, up=7, indpb=MUTATION_RATE)
    toolbox.register("select", tools.selBest)
    toolbox.register("evaluate", evaluate, key_signature=KEY, chord_seq=CHORD_SEQ, beats_per_bar=BEATS_PER_BAR)

    
    population = toolbox.population(n=POPULATION_SIZE)
    hf = tools.HallOfFame(1)
    
    #runs for each generation
    for gen in range(GENERATIONS):
        print(f"\nGeneration {gen + 1}:")
        offspring = algorithms.varAnd(population, toolbox, cxpb=CROSSOVER_RATE, mutpb=MUTATION_RATE)
        fits = toolbox.map(toolbox.evaluate, offspring)
        for fit, ind in zip(fits, offspring):
            ind.fitness.values = fit
        population = toolbox.select(offspring, k=len(population))
        hf.update(population)

        print("\nBest melody found:")
        best_individual = hf[0]
        best_melody = create_melody(best_individual, KEY, CHORD_SEQ, BEATS_PER_BAR)
        best_chords = create_chords(CHORD_SEQ, KEY, BEATS_PER_BAR)
        combined_stream = stream.Stream([best_melody, best_chords])
        combined_stream.write('midi', 'final_output.mid')

        midi_to_wav('final_output.mid', 'final_output.wav')

        print("Playing best melody and chords...")
        #combine_wav_files(['best_melody.wav', 'best_chords.wav'], 'final_output.wav')
        play_wav_file('final_output.wav')

if __name__ == "__main__":
       main()