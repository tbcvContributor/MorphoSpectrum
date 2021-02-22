import os
from midi import midi2piece
from parameters import *
from plots import plot_cqt
from signals import signal_from_file, wav, get_time_vector
from tqdm import tqdm
from time_frequency import cqt
from music import Note
import scipy.stats as stat


class SamplesSet(list):
    def __init__(self, instrument, samples_name=None, piece=None, signal=None):
        super().__init__()
        self.instrument = instrument
        self.samples_name = samples_name
        self.piece = piece
        self.signal = signal

    @classmethod
    def from_directory(cls, instrument, directory_path='samples', start_seconds=0., end_seconds=None, load_all=LOAD_ALL,
                       partials_distribution_type=PARTIALS_DISTRIBUTION_TYPE, verbose=True):
        """ Recover a Samples Set from a directory.

        Parameters
        ----------
            instrument: str
                Instrument from where the samples are taken.
            directory_path: str
                Directory (in relative path) from where the samples are retrieved. Default is 'samples'.
            start_seconds: float
                Starting time in seconds from where we take each sample. Default is 0.
            end_seconds: None, float
                Ending time in seconds up to where we take each sample. If None is passed as argument, the sample is
                taken up to the end. Default is None.
            load_all: bool
                If load_all is True the information of the sample will be loaded instead of computed.
            partials_distribution_type: str
                Type of partial distribution, i.e.: the decay behaviour of the partials. Default is set in parameters.
            verbose: bool
                If True then log info is emitted. Default True.

        Returns
        -------
            samples_set: SamplesSet
                The SamplesSet object obtained from the directory.
        """
        if verbose:
            log.info("Recovering samples from directory " + str(directory_path))

        samples_set = cls(instrument, samples_name=directory_path)
        # ToDo: load all as a principal parameter
        files = os.listdir(SAMPLES_AUDIO_PATH)

        sta = time.time()
        for file in tqdm(files):
            sample = Sample.from_file(file[:-4], start_seconds=start_seconds, load_all=load_all,
                                      end_seconds=end_seconds, partials_distribution_type=partials_distribution_type)
            samples_set.append(sample)
        end = time.time()
        if verbose:
            log.info("Time to recover samples: " + str(round(end - sta, 3)) + " seconds.")

        return samples_set

    def save(self, naming_by="midi_number", **kwargs):
        save_audio = kwargs['save_audio']
        save_array = kwargs['save_array']
        save_image = kwargs['save_image']
        save_info = kwargs['save_info']
        for sample in self:
            sample.save(save_audio=save_audio, save_array=save_array, save_image=save_image, save_info=save_info,
                        naming_by=naming_by)

    @classmethod
    def from_midi_file(cls, instrument, samples_name, resonance_seconds=0., naming_by="midi_number", save=True, verbose=True,
                       partials_distribution_type=PARTIALS_DISTRIBUTION_TYPE, **kwargs):
        """ Recover a Samples Set from a midi file and its corresponding audio file.

        Parameters
        ----------
            instrument: str
                Instrument from where the samples are taken.
            samples_name: str
                Name of the samples file without the extension. Should match also the name of the audio file without
                extension.
            resonance_seconds: float
                Time left after the note off message. Default is 0.
            partials_distribution_type: str
                Type of partial distribution, i.e.: the decay behaviour of the partials. Default is set in parameters.
            naming_by:
                The way naming the audio files if they are witten.
                    Options:
                        - midi_number: Naming the files by the note number in MIDI system.
                        - nameWithOctave: Naming the files by the name of the notes in the english system.
            save: bool
                If True then the sample is saved. Additional parameters should then be passed in kwargs:
                    - save_audio: bool
                    - save_array: bool
                    - save_image: bool
                    - save_info: bool
            verbose: bool
                If True then log info is emitted. Default True.

        Returns
        -------
            samples_set: SamplesSet
                The SamplesSet object obtained from the directory.
        """

        if verbose:
            log.info("Recovering samples from midi file " + str(samples_name))

        piece = midi2piece(samples_name)
        signal = signal_from_file(samples_name)

        samples_set = cls(instrument, samples_name=samples_name, piece=piece, signal=signal)

        sta = time.time()
        for note in tqdm(piece):
            start_samples = np.floor(note.start_seconds * FS).astype(int)
            end_samples = np.ceil((note.end_seconds + resonance_seconds) * FS).astype(int)
            note_signal = signal[start_samples:end_samples]

            spectrogram, spectrogram_log, time_vector = Sample.get_spectrogram(note_signal)
            fundamental_bin, partials_bins = Sample.get_partials_bins(note.note_number)
            partials_amplitudes, partials_distribution = Sample.get_partials_info(spectrogram_log, partials_bins,
                                                                                  time_vector,
                                                                                  partials_distribution_type)

            sample = Sample(note.velocity, note.note_number, note.start_seconds, note.end_seconds, note_signal,
                            spectrogram_log, time_vector, fundamental_bin, partials_bins, partials_amplitudes,
                            partials_distribution)

            samples_set.append(sample)
            if save:
                sample.save(save_audio=kwargs['save_audio'], save_array=kwargs['save_array'],
                            save_image=kwargs['save_image'], save_info=kwargs['save_info'], naming_by=naming_by)
        end = time.time()
        if verbose:
            log.info("Time to recover samples: " + str(round(end - sta, 3)) + " seconds.")

        return samples_set


class Sample(Note):
    def __init__(self, velocity, note_number, start_seconds, end_seconds, signal, spectrogram_log, time_vector,
                 fundamental_bin, partials_bins, partials_amplitudes, partials_distribution, file_name=None):
        super().__init__(note_number, velocity, start_seconds, end_seconds)
        self.file_name = file_name
        self.fundamental_bin = fundamental_bin
        self.partials_bins = partials_bins
        self.signal = signal
        self.spectrogram_log = spectrogram_log
        self.time_vector = time_vector
        self.partials_amplitudes = partials_amplitudes
        self.partials_distribution = partials_distribution

    def __str__(self, *kwargs):
        result = ""
        result += self.pitch.unicodeNameWithOctave
        result += " (" + str(self.note_number) + ")"
        result += ", duration: " + str(round(self.duration, 3)) + " s"
        result += ", velocity: " + str(self.velocity)
        return result

    @classmethod
    def from_file(cls, file_name, load_all=LOAD_ALL, start_seconds=0., end_seconds=None, audio_path=SAMPLES_AUDIO_PATH,
                  partials_distribution_type=PARTIALS_DISTRIBUTION_TYPE):
        signal = signal_from_file(file_name, audio_path=audio_path)
        if end_seconds:
            signal_cut = signal[np.floor(start_seconds * FS).astype(int): np.ceil(end_seconds * FS).astype(int)]
        else:
            signal_cut = signal[np.floor(start_seconds * FS).astype(int):]
            end_seconds = signal_cut.size / FS

        parameters = file_name.split("_")
        note_number = int(parameters[0])
        duration = float(parameters[1])
        end_seconds = min(end_seconds, duration)
        velocity = int(parameters[2])

        if load_all:
            time_vector = get_time_vector(signal_cut)
            spectrogram = np.load(Path(SAMPLES_ARRAYS_PATH) / Path(file_name + "_spectrogram.npy"))
            partials_bins = np.load(Path(SAMPLES_INFO_PATH) / Path(file_name + "_bins.npy"))
            fundamental_bin = partials_bins[0]
            partials_amplitudes = np.load(Path(SAMPLES_INFO_PATH) / Path(file_name + "_amplitudes.npy"))
            partials_distribution = np.load(Path(SAMPLES_INFO_PATH) / Path(file_name + "_distribution.npy"))
        else:
            spectrogram, time_vector = cqt(signal_cut)
            fundamental_bin, partials_bins = Sample.get_partials_bins(note_number)
            partials_amplitudes, partials_distribution = Sample.get_partials_info(spectrogram, partials_bins,
                                                                                  time_vector,
                                                                                  partials_distribution_type)

        return cls(velocity, note_number, 0, end_seconds, signal_cut, spectrogram, time_vector, fundamental_bin,
                   partials_bins, partials_amplitudes, partials_distribution, file_name=file_name)

    @staticmethod
    def get_partials_bins(note_number):
        fundamental_bin = np.round(((note_number - NUMBER_F_MIN) / 12) * BINS_PER_OCTAVE).astype(int)
        partials_bins = fundamental_bin + np.round(np.log2(np.arange(N_PARTIALS) + 1) * BINS_PER_OCTAVE).astype(int)
        partials_bins_allowed = partials_bins[partials_bins < N_BINS]

        return fundamental_bin, partials_bins_allowed

    @staticmethod
    def get_partials_info(spectrogram_log, partials_bins, time_vector, partials_distribution_type, plot_regress=False):
        partials_amplitudes = spectrogram_log[partials_bins, :]

        if partials_distribution_type == 'linear':
            linear_regressions = np.empty((partials_amplitudes.shape[0], 5))
            for i in range(partials_amplitudes.shape[0]):
                time_vector_over_noise = time_vector[partials_amplitudes[i] >= NOISE_THRESHOLD]
                partials_amplitudes_over_noise = partials_amplitudes[i, partials_amplitudes[i] >= NOISE_THRESHOLD]

                if partials_amplitudes_over_noise.size == 0:
                    time_vector_over_noise = time_vector[0:2]
                    partials_amplitudes_over_noise = partials_amplitudes[i, 0:2]
                elif partials_amplitudes_over_noise.size == 1:
                    time_vector_over_noise = time_vector[0:2]
                    partials_amplitudes_over_noise = partials_amplitudes[i, 0:2]

                linear_regression = stat.linregress(time_vector_over_noise, partials_amplitudes_over_noise)
                linear_regressions[i, :] = linear_regression

                if plot_regress:
                    Sample.plot_regression(linear_regression, time_vector_over_noise, partials_amplitudes_over_noise)

            partials_distribution = LinearPartialsDistribution(partials_amplitudes, linear_regressions)
        else:
            raise Exception("Partials distribution type not understood.")

        return partials_amplitudes, partials_distribution

    @staticmethod
    def plot_regression(linear_regression, time_vector_under_noise, partials_amplitudes_under_noise):
        plt.figure()
        plt.plot(time_vector_under_noise, partials_amplitudes_under_noise, 'o', label='original data')
        plt.plot(time_vector_under_noise, linear_regression.intercept +
                 linear_regression.slope * time_vector_under_noise, 'r', label='fitted line')
        plt.legend()
        plt.show()

    def create_strel(self):
        self.file_name = self.file_name
        raise Exception("Functionality not implemented.")

    def save(self, save_audio=False, save_array=True, save_image=True, save_info=True, naming_by="midi_number"):
        # The output_name for the saving data
        if naming_by == "midi_number":
            output_name = str(self.note_number) + "_" + str(round(self.duration, 3)) \
                          + "_" + str(self.velocity)
        elif naming_by == "nameWithOctave":
            output_name = self.pitch.nameWithOctave + "_" + str(round(self.duration, 3)) \
                          + "_" + str(self.velocity)
        else:
            raise Exception("Parameter naming_by not understood.")

        # Save the audio
        if save_audio:
            wav.write(Path(SAMPLES_AUDIO_PATH) / Path(output_name + '.wav'), FS, self.signal)

        # Save array
        if save_array:
            np.save(Path(SAMPLES_ARRAYS_PATH) / Path(output_name + '_spectrogram' + '.npy'), self.spectrogram_log,
                    allow_pickle=True)

        # Save image
        if save_image:
            plot_cqt(self.spectrogram_log, self.time_vector, fig_title="Sample " + str(self), show=False)
            plt.savefig(Path(SAMPLES_IMAGES_PATH) / Path(output_name + '.png'), dpi=DPI, format='png')
            plt.close()
        # Save info
        if save_info:
            np.save(Path(SAMPLES_INFO_PATH) / Path(output_name + '_distribution' + '.npy'),
                    self.partials_distribution.linear_regressions, allow_pickle=True)
            np.save(Path(SAMPLES_INFO_PATH) / Path(output_name + '_bins' + '.npy'), self.partials_bins,
                    allow_pickle=True)
            np.save(Path(SAMPLES_INFO_PATH) / Path(output_name + '_amplitudes' + '.npy'), self.partials_amplitudes,
                    allow_pickle=True)


class PartialsDistribution:
    def __init__(self, partials_amplitudes, distribution_type=None):
        self.partials_amplitudes = partials_amplitudes
        self.number_partials = partials_amplitudes.shape[0]
        self.distribution_type = distribution_type


class LinearPartialsDistribution(PartialsDistribution):
    def __init__(self, partials_amplitudes, linear_regressions):
        super().__init__(partials_amplitudes, distribution_type="linear")
        self.slopes = linear_regressions[:, 0]
        self.intercept = linear_regressions[:, 1]
        self.rvalue = linear_regressions[:, 2]
        self.pvalue = linear_regressions[:, 3]
        self.stderr = linear_regressions[:, 4]
        self.linear_regressions = linear_regressions


if __name__ == '__main__':
    _samples_name = 'samples'
    _instrument = "MyPiano"

    # _samples_set = SamplesSet.from_directory("MyPiano", "samples", load_all=LOAD_ALL)
    _samples_set = SamplesSet.from_midi_file("MyPiano", "samples", save_audio=True, save_array=True,
                                             save_image=True, save_info=True)
