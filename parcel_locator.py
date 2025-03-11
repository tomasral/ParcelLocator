# -*- coding: utf-8 -*-
"""
Parcel Locator - Plugin de QGIS para buscar parcelas por referencia catastral
o por Provincia, Municipio, Polígono y Parcela.
"""
from qgis.PyQt.QtWidgets import QAction, QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox, QFrame
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsPointXY,  QgsField
from .resources import *
from PyQt5.QtCore import QVariant
from qgis.gui import QgsMapCanvas
import requests
import os
import xml.etree.ElementTree as ET

def classFactory(iface):
    return ParcelLocator(iface)

class ParcelLocator(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = QAction(QIcon(os.path.join(self.plugin_dir, "icon.png")), "Parcel Locator", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        
    def initGui(self):
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("Parcel Locator", self.action)
    
    def run(self):
        self.dialog = QDialog(self.iface.mainWindow())
        self.dialog.setWindowTitle("Parcel Locator")
        layout = QVBoxLayout()
        
        # Campo de texto para la referencia catastral
        self.ref_catastral_label = QLabel("Introduce la referencia catastral (14 caracteres):")
        layout.addWidget(self.ref_catastral_label)
        
        self.ref_catastral_input = QLineEdit()
        self.ref_catastral_input.setMaxLength(14)
        layout.addWidget(self.ref_catastral_input)

        # Añadir separador
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("Si no conoces la referencia catastral puedes buscarla aquí:"))
        
        # Búsqueda por Provincia, Municipio, Polígono y Parcela
        self.provincia_label = QLabel("Selecciona una provincia:")
        layout.addWidget(self.provincia_label)
        self.provincia_dropdown = QComboBox()
        self.provincia_dropdown.currentIndexChanged.connect(self.update_municipios)
        layout.addWidget(self.provincia_dropdown)
        
        self.municipio_label = QLabel("Selecciona un municipio:")
        layout.addWidget(self.municipio_label)
        self.municipio_dropdown = QComboBox()
        layout.addWidget(self.municipio_dropdown)
        
        self.poligono_label = QLabel("Introduce el polígono:")
        layout.addWidget(self.poligono_label)
        self.poligono_input = QLineEdit()
        layout.addWidget(self.poligono_input)
        
        self.parcela_label = QLabel("Introduce la parcela:")
        layout.addWidget(self.parcela_label)
        self.parcela_input = QLineEdit()
        layout.addWidget(self.parcela_input)
        
        # Botón para obtener la referencia catastral
        self.get_ref_button = QPushButton("Obtener referencia catastral")
        self.get_ref_button.clicked.connect(self.get_ref_catastral)
        layout.addWidget(self.get_ref_button)

        # Otra sección con otro separador
        layout.addWidget(QLabel(""))

        # Selección del SRS
        self.srs_label = QLabel("Selecciona el Sistema de Referencia Espacial (SRS):")
        layout.addWidget(self.srs_label)
        
        self.srs_dict = {
            "EPSG:4230": "Geográficas en ED 50",
            "EPSG:4326": "Geográficas en WGS 80",
            "EPSG:4258": "Geográficas en ETRS89",
            "EPSG:32627": "UTM huso 27N en WGS 84",
            "EPSG:32628": "UTM huso 28N en WGS 84",
            "EPSG:32629": "UTM huso 29N en WGS 84",
            "EPSG:32630": "UTM huso 30N en WGS 84",
            "EPSG:32631": "UTM huso 31N en WGS 84",
            "EPSG:25829": "UTM huso 29N en ETRS89",
            "EPSG:25830": "UTM huso 30N en ETRS89",
            "EPSG:25831": "UTM huso 31N en ETRS89",
            "EPSG:23029": "UTM huso 29N en ED50",
            "EPSG:23030": "UTM huso 30N en ED50",
            "EPSG:23031": "UTM huso 31N en ED50"
        }
        
        self.srs_dropdown = QComboBox()
        for code, name in self.srs_dict.items():
            self.srs_dropdown.addItem(f"{code} - {name}", code)
        layout.addWidget(self.srs_dropdown)
        
        self.srs_button = QPushButton("Seleccionar SRS del proyecto")
        self.srs_button.clicked.connect(self.set_project_srs)
        layout.addWidget(self.srs_button)

        # Otra sección con otro separador
        layout.addWidget(QLabel(""))

        # Botón de búsqueda
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.process_input)
        layout.addWidget(self.search_button)
        
        # Establecer el diseño
        self.dialog.setLayout(layout)
        # Cargar provincias al iniciar el plugin
        self.load_provincias()
        # Mostrar la ventana del plugin
        self.dialog.exec_()
    


    def set_project_srs(self):
        project_srs = self.iface.mapCanvas().mapSettings().destinationCrs().authid()
        if project_srs in self.srs_dict:
            self.srs_dropdown.setCurrentText(f"{project_srs} - {self.srs_dict[project_srs]}")
        else:
            QMessageBox.warning(self.dialog, "Error", "El SRS del proyecto no es compatible con la lista disponible.")
            
    def load_provincias(self):
        """Carga la lista de provincias desde el servicio web del Catastro."""
        url = "http://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/rest/ObtenerProvincias"
        response = requests.get(url)
        
        if response.status_code != 200:
            QMessageBox.warning(self.dialog, "Error", "No se pudo obtener la lista de provincias.")
            return
        
        data = response.text
        root = ET.fromstring(data)
        ns = {'ns': 'http://www.catastro.meh.es/'}

        self.provincia_dropdown.clear()
        self.provincia_dropdown.addItem("Selecciona una provincia", "")

        for prov in root.findall(".//ns:prov", ns):
            nombre = prov.find("ns:np", ns)
            if nombre is not None:
                self.provincia_dropdown.addItem(nombre.text, nombre.text)
        
    def update_municipios(self):
        """Carga la lista de municipios según la provincia seleccionada."""
        provincia_name = self.provincia_dropdown.currentText()
        if not provincia_name or provincia_name == "Selecciona una provincia":
            return

        url = "http://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/rest/ObtenerMunicipios"
        headers = {
            "Content-Type": "text/xml",
            "Accept": "text/xml"
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
        <MunicipiosRest_In xmlns="http://www.catastro.meh.es/">
          <Provincia>{provincia_name}</Provincia>
        </MunicipiosRest_In>"""

        response = requests.post(url, data=body.encode('utf-8'), headers=headers)
        
        if response.status_code != 200:
            QMessageBox.warning(self.dialog, "Error", "No se pudo obtener la lista de municipios.")
            return

        data = response.text
        root = ET.fromstring(data)
        ns = {'ns': 'http://www.catastro.meh.es/'}

        self.municipio_dropdown.clear()
        self.municipio_dropdown.addItem("Selecciona un municipio", "")

        municipios_element = root.find(".//ns:municipiero", ns)
        if municipios_element is None:
            QMessageBox.warning(self.dialog, "Error", "No se encontraron municipios para la provincia seleccionada.")
            return

        for muni in municipios_element.findall("ns:muni", ns):
            nombre = muni.find("ns:nm", ns)
            if nombre is not None:
                self.municipio_dropdown.addItem(nombre.text, nombre.text)

    def get_ref_catastral(self):
        provincia = self.provincia_dropdown.currentText()
        municipio = self.municipio_dropdown.currentText()
        poligono = self.poligono_input.text()
        parcela = self.parcela_input.text()

        if not provincia or not municipio or not poligono or not parcela:
            QMessageBox.warning(self.dialog, "Error", "Debes completar todos los campos.")
            return

        # Realizar la consulta para obtener la referencia catastral
        url = "http://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/rest/Consulta_DNPPP"
        headers = {"Content-Type": "application/xml"}
        body = f"""<?xml version="1.0" encoding="utf-8"?>
        <ConsultaRest_DNPPP_In xmlns="http://www.catastro.meh.es/">
          <Provincia>{provincia}</Provincia>
          <Municipio>{municipio}</Municipio>
          <Poligono>{poligono}</Poligono>
          <Parcela>{parcela}</Parcela>
        </ConsultaRest_DNPPP_In>"""
        response = requests.post(url, data=body.encode("utf-8"), headers=headers)
        
        ##
        if response.status_code != 200:
            QMessageBox.warning(self.dialog, "Error", "Error al realizar la búsqueda.")
            return

        # Procesar y mostrar los resultados
        root = ET.fromstring(response.text)
        ns = {'ns': 'http://www.catastro.meh.es/'}
        ref_cat = root.find(".//ns:pc1", ns).text + root.find(".//ns:pc2", ns).text if root.find(".//ns:pc1", ns) is not None else "No encontrada"
        details = root.find(".//ns:ldt", ns).text if root.find(".//ns:ldt", ns) is not None else "Sin detalles"
        use = root.find(".//ns:luso", ns).text if root.find(".//ns:luso", ns) is not None else "No disponible"
        msg = f"Referencia Catastral: {ref_cat}\nDetalles: {details}\nUso: {use}"
        QMessageBox.information(self.iface.mainWindow(), "Información de la Parcela", msg)     

        ##
        root = ET.fromstring(response.text)

        ref_cat_pc1 = root.find(".//ns:pc1", ns)
        ref_cat_pc2 = root.find(".//ns:pc2", ns)

        if ref_cat_pc1 is not None and ref_cat_pc2 is not None:
            self.ref_catastral_input.setText(ref_cat_pc1.text + ref_cat_pc2.text)
        else:
            QMessageBox.critical(self.dialog, "Error", "No se encontró la referencia catastral.")

    def process_input(self):
        ref_catastral = self.ref_catastral_input.text().strip()
        if len(ref_catastral) != 14:
            QMessageBox.critical(self.dialog, "Error", "La referencia catastral debe tener exactamente 14 caracteres.")
            return
        
        srs = self.srs_dropdown.currentData()
        datos = self.get_coordinates(ref_catastral, srs)
        if datos:
            coords, detalles = datos
            self.zoom_to_location(coords)
            QMessageBox.information(self.iface.mainWindow(), "Información Catastral", detalles)
        else:
            QMessageBox.critical(self.iface.mainWindow(), "Error", "No se encontraron datos para la referencia catastral.")

    def get_coordinates(self, ref_catastral, srs):
        url = f"http://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/Consulta_CPMRC?SRS={srs}&RefCat={ref_catastral}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if "Consulta_CPMRCResult" in data and "coordenadas" in data["Consulta_CPMRCResult"]:
                coord_data = data["Consulta_CPMRCResult"]["coordenadas"]["coord"][0]
                xcen = float(coord_data["geo"]["xcen"])
                ycen = float(coord_data["geo"]["ycen"])
                direccion = coord_data.get("ldt", "Dirección no disponible")
                detalles = f"Referencia Catastral: {ref_catastral}\nDirección: {direccion}\nCoordenadas: ({xcen}, {ycen})"
                return (xcen, ycen), detalles
            else:
                return None
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self.iface.mainWindow(), "Error", f"Error de conexión con el Catastro: {str(e)}")
            return None
        except KeyError:
            QMessageBox.critical(self.iface.mainWindow(), "Error", "La estructura de la respuesta del Catastro ha cambiado.")
            return None

    def zoom_to_location(self, coords):
        if not coords:
            QMessageBox.critical(self.iface.mainWindow(), "Error", "No se pudieron obtener las coordenadas.")
            return
        lon, lat = coords
        canvas = self.iface.mapCanvas()
        point = QgsPointXY(lon, lat)
        canvas.setCenter(point)
        canvas.zoomScale(500)
        canvas.refresh()
    
    def unload(self):
        """Elimina el plugin de la interfaz de QGIS."""
        self.iface.removePluginMenu("Parcel Locator", self.action)
        self.iface.removeToolBarIcon(self.action)
