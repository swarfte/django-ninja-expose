import uuid

from django.db import models

from django_ninja_expose import expose


@expose()
class Project(models.Model):
    name = models.CharField(max_length=100)


@expose()
class Tag(models.Model):
    label = models.CharField(max_length=50)


@expose(path="tasks", query=["priority", "completed", "created_at"])
class Task(models.Model):
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True, default="")
    priority = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    due = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag, blank=True)


@expose()
class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=50)


@expose(methods=["get", "post"], fields=["id", "title"], query=[])
class Memo(models.Model):
    title = models.CharField(max_length=50)
    secret = models.CharField(max_length=50, default="x")
