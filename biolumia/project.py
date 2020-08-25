
import json 
import os

from PySide2.QtCore import QRect


class Project(object):

	def __init__(self, filename = None):

		self.raw = {
		"project_name": "",
		"group_files": [],
		"areas": []
		}

		if filename:
			self.load(filename)

	def load(self, filename):
		
		if not os.path.exists(filename):
			raise FileNotFoundError() 
		with open(filename, "r") as file:
			self.raw.update(json.load(open(filename)))
			

	def set_project_name(self, name):
		self.raw["project_name"] = name

	def get_project_name(self):
		return self.raw.get("project_name","")

	def add_group(self, group_name:str, files: list):
		gp = {
		"name" : group_name,
		"files": files
		}
		self.raw["group_files"].append(gp)

	def get_groups(self):
		return self.raw["group_files"]

	def add_area(self, rect: QRect):
		self.raw["areas"].append(self._rect_to_area(rect))

	def get_areas(self):
		rect_list = []
		for area in self.raw["areas"]:
			rect_list.append(self._area_to_rect(area))

		return rect_list

	def _area_to_rect(self, area: dict):

		x = area.get("x", 0)
		y = area.get("y",0)
		width = area.get("width", 0)
		height = area.get("height", 0)
		return QRect(x,y,width, height)

	def _rect_to_area(self, rect: QRect):

		return {
		"x": rect.left(),
		"y": rect.top(),
		"width": rect.width(),
		"height": rect.height()
		}


if __name__ == '__main__':

	pj = Project("../project_example.json")

	print(pj.get_groups())