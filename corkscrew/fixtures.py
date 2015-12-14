# coding: utf-8

from peewee import Proxy, Model, PrimaryKeyField, CharField, IntegerField, ForeignKeyField


database = Proxy()


class BaseModel(Model):
	class Meta:
		database = database


class Person(BaseModel):
	id = PrimaryKeyField()
	name = CharField()
	age = IntegerField()


class Photo(BaseModel):
	id = PrimaryKeyField()
	title = CharField()
	src = CharField()
	photographer = ForeignKeyField(Person)


class Tag(BaseModel):
	id = PrimaryKeyField()
	name = CharField(unique = True)


class Article(BaseModel):
	id = PrimaryKeyField()
	title = CharField()
	cover = ForeignKeyField(Photo, null = True)
	author = ForeignKeyField(Person)


class Comment(BaseModel):
	id = PrimaryKeyField()
	body = CharField()
	article = ForeignKeyField(Article, null = True)
	author = ForeignKeyField(Person)


class PhotoTag(BaseModel):
	photo = ForeignKeyField(Photo)
	tag = ForeignKeyField(Tag)



ARTICLE_TITLES = [
	"JSON API: Why It Is A Good Idea",
	"Visualization: A Picture Says More Than 1000 Words"
]

PERSON_NAMES = [
	"John Doe",
	"Jane Doe"
]

PERSON_AGES = [18, 22]

PHOTO_TITLE = "A New Beginning"
PHOTO_SRC = "https://example.com/test.jpg"

COMMENT_BODIES = [
	"First!",
	"You, Sir, WIN the Internet."
]

TAG_NAMES = [
	"example",
	"hashtag"
]


def insertFixtures():
	database.create_tables([Person, Photo, Tag, Comment, Article, PhotoTag])

	person1 = Person.create(name = PERSON_NAMES[0], age = PERSON_AGES[0])
	person2 = Person.create(name = PERSON_NAMES[1], age = PERSON_AGES[1])

	photo = Photo.create(
		title        = PHOTO_TITLE,
		src          = PHOTO_SRC,
		photographer = person1
	)

	article1 = Article.create(
		title  = ARTICLE_TITLES[0],
		author = person1
	)

	article2 = Article.create(
		title  = ARTICLE_TITLES[1],
		author = person1,
		cover  = photo
	)

	comment1 = Comment.create(
		body    = COMMENT_BODIES[0],
		article = article1,
		author  = person2
	)

	comment2 = Comment.create(
		body    = COMMENT_BODIES[1],
		article = article1,
		author  = person2
	)

	tag1 = Tag.create(name = TAG_NAMES[0])
	tag2 = Tag.create(name = TAG_NAMES[1])
	PhotoTag.create(tag = tag1, photo = photo)
	PhotoTag.create(tag = tag2, photo = photo)
