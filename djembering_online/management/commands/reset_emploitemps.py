from django.core.management.base import BaseCommand
from djembering_online.models import EmploiTemps  # adapte si ton app modèle est ailleurs

class Command(BaseCommand):
    help = "Remet tous les emplois du temps à Non effectué"

    def handle(self, *args, **kwargs):
        emplois = EmploiTemps.objects.all()

        for emploi in emplois:
            emploi.etat = "Non effectué"
            emploi.save()  # déclenche les signals si tu en as

        self.stdout.write(
            self.style.SUCCESS("Tous les emplois du temps ont été réinitialisés")
        )