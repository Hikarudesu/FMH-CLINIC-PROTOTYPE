from django.db import models
from django.conf import settings


class Pet(models.Model):
    """A pet belonging to a registered pet owner."""

    class Sex(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pets',
    )
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=60, help_text='e.g. Dog, Cat, Bird, Rabbit')
    breed = models.CharField(max_length=100, blank=True)
    age = models.PositiveIntegerField(help_text='Age in years')
    sex = models.CharField(max_length=10, choices=Sex.choices)
    color = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.species}) — {self.owner.username}'
