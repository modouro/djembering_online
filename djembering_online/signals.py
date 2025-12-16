from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from datetime import date

from .models import EmploiTemps, CalculHeures


@receiver(pre_save, sender=EmploiTemps)
def avant_sauvegarde_emploitemps(sender, instance, **kwargs):
    """
    Sauvegarde l'ancien état AVANT modification
    """
    if instance.pk:
        instance._ancien_etat = EmploiTemps.objects.get(pk=instance.pk).etat
    else:
        instance._ancien_etat = None


@receiver(post_save, sender=EmploiTemps)
def apres_sauvegarde_emploitemps(sender, instance, created, **kwargs):
    """
    Calcul automatique des heures après sauvegarde
    """

    calcul, _ = CalculHeures.objects.get_or_create(
        emploitemps=instance,
        defaults={
            'heures_dues': instance.professeur.heure_matiere,
            'heures_faites': 0,
            'heures_complementaires': 0,
        }
    )

    if created:
        return

    ancien = instance._ancien_etat
    nouveau = instance.etat

    if ancien != nouveau:
        duree = instance.duree_heures

        if ancien == 'Non effectué' and nouveau == 'Effectué':
            calcul.heures_faites += duree
        elif ancien == 'Effectué' and nouveau == 'Non effectué':
            calcul.heures_faites = max(calcul.heures_faites - duree, 0)

        calcul.heures_complementaires = max(
            0,
            calcul.heures_faites - calcul.heures_dues
        )
        calcul.date_changement = date.today()
        calcul.save()
