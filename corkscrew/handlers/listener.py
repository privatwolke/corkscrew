# coding: utf-8

class Listener(object):
	def before_create(self, request):
		pass

	def after_create(self, response):
		pass

	def before_list(self):
		pass

	def after_list(self, response):
		pass

	def before_get(self, _id):
		pass

	def after_get(self, response):
		pass

	def before_delete(self, _id):
		pass

	def after_delete(self, _id):
		pass

	def before_patch(self, request):
		pass

	def after_patch(self, response):
		pass
