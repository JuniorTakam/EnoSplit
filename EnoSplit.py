# importation des differents modules de PyQt5
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QMessageBox
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import pyqtSignal, QThread, QObject

# le fichier ressource
import rsc
#pyrcc5 -o rsc.py rsc.qrc


import os, sys, subprocess, threading
import pickle
import hashlib
import mimetypes
import tempfile
from datetime import datetime


class EnoProtect:
    def __init__(self, filepath):
        if filepath != "":
            self.filepath = filepath
            self.filename = os.path.splitext(os.path.basename(filepath))[0]
            self.extension = os.path.splitext(filepath)[1]

    def calculate_checksum(self, filepath):
        """Calculate the SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_parent_directory(self, file_path):
        # Utilise os.path.dirname pour obtenir le chemin du dossier parent
        parent_directory = os.path.dirname(file_path)
        return parent_directory

    def segment_file_by_number_of_segments(self, num_segments, progress_callback, fichiers_fragmentes_callback):
        original_checksum = self.calculate_checksum(self.filepath)
        with open(self.filepath, 'rb') as f:
            file_content = f.read()

        file_size = len(file_content)
        segment_size = file_size // num_segments
        segments = []

        current_datetime = datetime.now()
        current_datetime = current_datetime.strftime("%Y-%m-%d %H-%M-%S")

        for i in range(num_segments):
            start = i * segment_size
            end = None if i == num_segments - 1 else (i + 1) * segment_size
            segment_content = file_content[start:end]
            segment = {
                'filename': self.filename,
                'extension': self.extension,
                'position': i,
                'nbr_segments':num_segments,
                'content': segment_content,
                'original_checksum': original_checksum,
            }
            segments.append(segment)

            # creation du dossier de sorti

            path_output_dir = self.get_parent_directory(self.filepath) + f"/{self.filename+self.extension} " +  str(current_datetime)
            os.makedirs(path_output_dir, exist_ok=True)
            segment_filename = path_output_dir + f"/{self.filename}_{i}.eno"

            self.save_segment(segment, segment_filename)

            progress_callback.emit(int((i + 1) / num_segments * 100))
            fichiers_fragmentes_callback.emit(segment_filename)


        return segments

    def segment_file_by_max_size(self, max_fragment_size, progress_callback, fichiers_fragmentes_callback):
        original_checksum = self.calculate_checksum(self.filepath)
        with open(self.filepath, 'rb') as f:
            file_content = f.read()

        file_size = len(file_content)
        max_fragment_size = max_fragment_size -  1024
        num_segments = (file_size + max_fragment_size - 1) // max_fragment_size  # Calcul du nombre de segments
        segments = []

        current_datetime = datetime.now()
        current_datetime = current_datetime.strftime("%Y-%m-%d %H-%M-%S")

        for i in range(num_segments):
            start = i * max_fragment_size
            end = None if i == num_segments - 1 else (i + 1) * max_fragment_size
            segment_content = file_content[start:end]
            segment = {
                'filename': self.filename,
                'extension': self.extension,
                'position': i,
                'nbr_segments': num_segments,
                'content': segment_content,
                'original_checksum': original_checksum,
            }
            segments.append(segment)

            # creation du dossier de sorti

            path_output_dir = self.get_parent_directory(self.filepath) + f"/{self.filename + self.extension} " + str(
                current_datetime)
            os.makedirs(path_output_dir, exist_ok=True)
            segment_filename = path_output_dir + f"/{self.filename}_{i}.eno"

            self.save_segment(segment, segment_filename)

            progress_callback.emit(int((i + 1) / num_segments * 100))
            fichiers_fragmentes_callback.emit(segment_filename)

        return segments
    def save_segment(self, segment, segment_filename):
        with open(segment_filename, 'wb') as f:
            pickle.dump(segment, f)
            return 0

    def reform_file(self, list_segments_paths, output_dir, progress_callback, output_file_callback, error_callback):

        segments = []
        list_hash = []
        i = 0
        for segment_path in list_segments_paths:
            if not os.path.isfile(segment_path):
                error_callback.emit("le fichier "+ segment_path + " est introuvable")
                return False
            with open(segment_path, 'rb') as f:
                segment = pickle.load(f)
                hash = segment["original_checksum"]
                if i == 0 or i > 0 and hash in list_hash:
                    if segment not in segments:
                        segments.append(segment)
                list_hash.append(hash)
                i+=1

        if segments[0]["nbr_segments"] != len(segments):
            nbr_fichiers_manquants = segments[0]["nbr_segments"] - len(segments)
            error_callback.emit(str(nbr_fichiers_manquants) + " fichier(s) manquant(s)")
            return True

        output_extension = segments[0]["extension"]
        output_filename = segments[0]["filename"]
        segments.sort(key=lambda x: x['position'])
        file_content = b''.join(segment['content'] for segment in segments)

        output_filepath = output_dir + "/" + output_filename + output_extension

        with open(output_filepath, 'wb') as f:
            f.write(file_content)
            progress_callback.emit(100)
            output_file_callback.emit(output_filepath)


    def visualiser_file(self, list_segments_paths, error_callback):
        segments = []
        list_hash = []
        i = 0
        for segment_path in list_segments_paths:
            if not os.path.isfile(segment_path):
                error_callback.emit("le fichier " + segment_path + " est introuvable")
                return False
            with open(segment_path, 'rb') as f:
                segment = pickle.load(f)
                hash = segment["original_checksum"]
                if i == 0 or i > 0 and hash in list_hash:
                    if segment not in segments:
                        segments.append(segment)
                list_hash.append(hash)
                i += 1

        if segments[0]["nbr_segments"] != len(segments):
            nbr_fichiers_manquants = segments[0]["nbr_segments"] - len(segments)
            error_callback.emit(str(nbr_fichiers_manquants) + " fichier(s) manquant(s)")
            return True

        file_extension = segments[0]["extension"]
        segments.sort(key=lambda x: x['position'])
        file_content = b''.join(segment['content'] for segment in segments)
        self.open_binary_content(file_content, file_extension, error_callback)

    def open_binary_content(self, content, file_extension, error_callback):
        try:
            # Crée un fichier temporaire en mémoire
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(content)
                temp_file.seek(0)  # Assurez-vous que le curseur de fichier est au début

                # Détermine le type MIME du fichier en fonction de l'extension
                mime_type, _ = mimetypes.guess_type(f"temp_file{file_extension}")

                # Ouvre le fichier temporaire avec l'application par défaut
                with open(temp_file.name, 'rb') as file:
                    subprocess.Popen(['start', '', temp_file.name], shell=True)  # Pour Windows
        except Exception as e:
            error_callback.emit(f"Erreur lors de l'ouverture du fichier : {e}")


class WorkerSegment(QThread):
    progress = pyqtSignal(int)
    fichiers_fragmentes = pyqtSignal(str)
    def __init__(self, filepath, method_seg, param_seg):
        super().__init__()
        self.filepath = filepath
        self.param_seg = param_seg
        self.method_seg = method_seg

    def run(self):
        enoprotect = EnoProtect(self.filepath)
        if self.method_seg == "size":
            enoprotect.segment_file_by_max_size(self.param_seg, self.progress, self.fichiers_fragmentes)
        if self.method_seg == "number":
            enoprotect.segment_file_by_number_of_segments(self.param_seg, self.progress, self.fichiers_fragmentes)


class WorkerReform(QThread):
    progress = pyqtSignal(int)
    output_file = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, list_segments, output_dir, method="reformer"):
        super().__init__()
        self.list_segments = list_segments
        self.output_dir = output_dir
        self.method = method

    def run(self):
        enoprotect = EnoProtect("")
        if self.method == "reformer":
            enoprotect.reform_file(self.list_segments, self.output_dir, self.progress, self.output_file, self.error)
        if self.method == "visualiser":
            enoprotect.visualiser_file(self.list_segments,self.error)


class BlinkSignal(QObject):
    update_color = pyqtSignal(str)


class BlinkingButton:
    def __init__(self, button, style_base):
        self.button = button
        self.style_base = style_base
        self.blink_signal = BlinkSignal()
        self.blink_signal.update_color.connect(self.change_color)
        self.blink_thread = None
        self._stop_event = threading.Event()

    def start_blinking(self):
        if self.blink_thread is None or not self.blink_thread.is_alive():
            self._stop_event.clear()
            self.blink_thread = threading.Thread(target=self._blink)
            self.blink_thread.start()

    def stop_blinking(self):
        if self.blink_thread is not None:
            self._stop_event.set()
            self.blink_thread.join()
        self.button.setStyleSheet(self.style_base + "background-color: green")

    def _blink(self):
        while not self._stop_event.is_set():
            self.blink_signal.update_color.emit("green")
            self._stop_event.wait(0.5)
            self.blink_signal.update_color.emit("white")
            self._stop_event.wait(0.5)

    def change_color(self, color):
        self.button.setStyleSheet(self.style_base + f"background-color: {color}")

class EnoSplitApp(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        loadUi(self.resource_path('EnoSplit 1.0.ui'), self)
        # definir une icon au logiciel
        pixmap = QtGui.QPixmap(self.resource_path("logo2.png"))
        icon = QtGui.QIcon(pixmap)
        self.setWindowIcon(icon)
        self.resize(550, 840)  # redimentionnemnet de la fenetre

        # barre de titre
        self.pushButton_a_propos.clicked.connect(self.a_propos_de_nous)
        self.blinking_button = BlinkingButton(self.pushButton_statut_on, self.pushButton_statut_on.styleSheet())


        # fragmentation
        self.pushButton_fragmenter.clicked.connect(self.afficher_menu_fragmentation)
        self.style_base_bouton = self.pushButton_fragmenter.styleSheet()
        self.pushButton_selectionner_un_fichier.clicked.connect(self.selectionner_un_fichier)
        self.liste_des_fichiers_selectionne = []
        self.lineEdit_valeur_parametre_fragmentation.setValidator(QIntValidator())
        self.progressBar_fragmentation.setValue(0)
        self.pushButton_segmenter.clicked.connect(self.segmenter_fichier)
        self.radioButton_nbr_segments.setChecked(True)

        # défragmentation
        self.pushButton_defragmenter.clicked.connect(self.afficher_menu_defragmentation)
        self.groupBox_defragmenter.setVisible(False)
        self.pushButton_selectionner_fragments.clicked.connect(self.selectionner_fragments)
        self.pushButton_ajouter_fragments.clicked.connect(self.ajouter_fragments)
        self.liste_des_fragments = []
        self.progressBar_defragmentation.setValue(0)
        self.pushButton_visualiser.clicked.connect(self.visualiser_fichier)
        self.pushButton_output_directory.clicked.connect(self.selectionner_output_directory)
        self.pushButton_reformer.clicked.connect(self.reformer_fichier)
        self.pushButton_ouvrir_fichier_sortir.clicked.connect(self.ouvrir_fichier_sortir)


    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
    def afficher_menu_fragmentation(self):
        self.groupBox_defragmenter.setVisible(False)
        self.groupBox_fragmenter.setVisible(True)

        self.pushButton_fragmenter.setStyleSheet(self.style_base_bouton + "border-color:rgba(200, 200, 200,200);")
        self.pushButton_defragmenter.setStyleSheet(self.style_base_bouton + "border-color:rgba(30, 42, 25,255);")

    def afficher_menu_defragmentation(self):
        self.groupBox_fragmenter.setVisible(False)
        self.groupBox_defragmenter.setVisible(True)

        self.pushButton_fragmenter.setStyleSheet(self.style_base_bouton + "border-color:rgba(30, 42, 25,255);")
        self.pushButton_defragmenter.setStyleSheet(self.style_base_bouton + "border-color:rgba(200, 200, 200,200);")

    def selectionner_un_fichier(self):
        # Explorateur de fichier
        self.fileDialog = QtWidgets.QFileDialog()
        self.fileDialog.setFileMode(self.fileDialog.ExistingFiles)

        # self.fileDialog.setFileMode()
        if self.fileDialog.exec_():
            filedir = self.fileDialog.selectedFiles()
            self.liste_des_fichiers_selectionne = []
            for file in filedir:
                if file not in self.liste_des_fichiers_selectionne:

                    self.liste_des_fichiers_selectionne.append(file)
                    self.lineEdit_fichier_selectionne.setText(file)

    def segmenter_fichier(self):
        self.listWidget_fichiers_fragmentes.clear()
        self.progressBar_fragmentation.setValue(0)

        filepath = self.lineEdit_fichier_selectionne.text()
        if not filepath:
            self.show_error("Veuillez sélectionner un fichier.")
            return
        if not self.lineEdit_valeur_parametre_fragmentation.text():
            self.show_error("Veuillez entrer un paramètre de segmentation valide")
            return

        # on desactive le bouton pour segmenter
        self.pushButton_segmenter.setEnabled(False)

        # faire clignotter le bouton
        self.blinking_button.start_blinking()

        if self.radioButton_taille_max_segment.isChecked():
            param_seg = int(self.lineEdit_valeur_parametre_fragmentation.text()) * 1024 * 1024
            self.worker = WorkerSegment(filepath, "size", param_seg)
            self.worker.progress.connect(self.update_progress)
            self.worker.fichiers_fragmentes.connect(self.update_fichiers_fragmentes)
            self.worker.start()
            self.worker.finished.connect(self.segment_finished)

        else:
            param_seg = int(self.lineEdit_valeur_parametre_fragmentation.text())
            self.worker = WorkerSegment(filepath, "number", param_seg)
            self.worker.progress.connect(self.update_progress)
            self.worker.fichiers_fragmentes.connect(self.update_fichiers_fragmentes)
            self.worker.start()
            self.worker.finished.connect(self.segment_finished)

    def update_progress(self, value):
        self.progressBar_fragmentation.setValue(value)
    def update_fichiers_fragmentes(self, path):
        self.listWidget_fichiers_fragmentes.addItems([path])

    def segment_finished(self):
        self.pushButton_segmenter.setEnabled(True)
        self.blinking_button.stop_blinking()
        self.show_status("Segmentation terminée.")


    def selectionner_fragments(self):
        self.liste_des_fragments = []
        self.listWidget_fichiers_a_defragmenter.clear()
        # Explorateur de fichier
        self.fileDialog = QtWidgets.QFileDialog()
        self.fileDialog.setFileMode(self.fileDialog.ExistingFiles)

        self.fileDialog.setNameFilter("Fichiers ENO (*.eno)")
        if self.fileDialog.exec_():
            filedir = self.fileDialog.selectedFiles()
            for file in filedir:
                if file not in self.liste_des_fragments:

                    self.liste_des_fragments.append(file)
            self.listWidget_fichiers_a_defragmenter.addItems(filedir)

    def ajouter_fragments(self):
        # Explorateur de fichier
        self.fileDialog = QtWidgets.QFileDialog()
        self.fileDialog.setFileMode(self.fileDialog.ExistingFiles)

        self.fileDialog.setNameFilter("Fichiers ENO (*.eno)")
        if self.fileDialog.exec_():
            filedir = self.fileDialog.selectedFiles()

            for file in filedir:
                if file not in self.liste_des_fragments:
                    self.liste_des_fragments.append(file)
            self.listWidget_fichiers_a_defragmenter.clear()
            self.listWidget_fichiers_a_defragmenter.addItems(self.liste_des_fragments)

    def visualiser_fichier(self):

        list_segments = self.liste_des_fragments
        if not list_segments:
            self.show_error("Veuillez sélectionner les segments.")
            return

        # on desactive le bouton pour visualiser
        self.pushButton_visualiser.setEnabled(False)

        # faire clignotter le bouton
        self.blinking_button.start_blinking()

        self.worker = WorkerReform(list_segments, "", "visualiser")
        self.worker.error.connect(self.show_error)
        self.worker.start()
        self.worker.finished.connect(self.visualiser_finished)
    def visualiser_finished(self):
        self.pushButton_visualiser.setEnabled(True)
        self.blinking_button.stop_blinking()
        self.show_status("Le fichier a été ouvert avec succès")

    def selectionner_output_directory(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Sélectionner un dossier')
        if folder:
            # Si un dossier est sélectionné, met à jour le label avec le chemin du dossier
            self.lineEdit_output_directory.setText(folder)
        else:
            # Si aucun dossier n'est sélectionné, affiche un message approprié
            self.lineEdit_output_directory.setText('Veuillez choisir un emplacement de sortir ...')

    def reformer_fichier(self):
        self.progressBar_defragmentation.setValue(0)

        #self.listWidget_fichiers_fragmentes.clear()
        list_segments = self.liste_des_fragments
        output_dir = self.lineEdit_output_directory.text()
        if not list_segments:
            self.show_error("Veuillez sélectionner les segments.")
            return

        if not os.path.isdir(output_dir):
            self.show_error("Veuillez choisir un emplacement de sortir pour stocker le fichier reconstitué")
            return

        # on desactive le bouton pour reformer
        self.pushButton_reformer.setEnabled(False)

        # faire clignotter le bouton
        self.blinking_button.start_blinking()

        self.worker = WorkerReform(list_segments, output_dir)
        self.worker.progress.connect(self.update_progress_reformer)
        self.worker.output_file.connect(self.update_output_file)
        self.worker.error.connect(self.show_error)
        self.worker.start()
        self.worker.finished.connect(self.reformer_finished)
    def reformer_finished(self):
        self.pushButton_reformer.setEnabled(True)
        self.blinking_button.stop_blinking()
        self.show_status("Fichier reformé avec succès.")

    def update_progress_reformer(self, value):
        self.progressBar_defragmentation.setValue(value)
    def update_output_file(self, value):
        self.lineEdit_result_defragmentation.setText(value)

    def ouvrir_fichier_sortir(self):
        output_file = self.lineEdit_result_defragmentation.text()
        if os.path.isfile(output_file):
            subprocess.Popen(['start', '', output_file], shell=True)
        else:
            self.show_error("Impossible de trouver le fichier")

    def show_error(self, message):
        QMessageBox.critical(self, "Erreur", message)
    def show_status(self, message):
        QMessageBox.information(self, "Info", message)

    def a_propos_de_nous(self):
        self.apropos_windows = QtWidgets.QMainWindow()
        self.apropos_windows.setGeometry(
            QtCore.QRect(self.x() + int(self.width() / 2) - 130-120 - 15, self.y() + int(self.height() / 2) - 50-60, 200, 147))
        loadUi(self.resource_path("aPropos.ui"), self.apropos_windows)
        # definir une icon au logiciel
        pixmap = QtGui.QPixmap(self.resource_path("logo2.png"))
        icon = QtGui.QIcon(pixmap)
        self.apropos_windows.setWindowIcon(icon)
        # rend modale la 2ème fenêtre (la 1ère fenêtre sera inactive)
        self.apropos_windows.setWindowModality(QtCore.Qt.ApplicationModal)

        # affiche la 2ème fenêtre
        self.apropos_windows.show()


app = QtWidgets.QApplication(sys.argv)
mainWindow = EnoSplitApp()
mainWindow.show()
sys.exit(app.exec_())

