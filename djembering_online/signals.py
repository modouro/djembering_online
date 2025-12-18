from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from datetime import date
from .models import EmploiTemps, CalculHeures


@receiver(pre_save, sender=EmploiTemps)
def avant_sauvegarde_emploitemps(sender, instance, **kwargs):
    if instance.pk:
        instance._ancien_etat = EmploiTemps.objects.get(pk=instance.pk).etat
    else:
        instance._ancien_etat = None


@receiver(post_save, sender=EmploiTemps)
def apres_sauvegarde_emploitemps(sender, instance, created, **kwargs):

    calcul, _ = CalculHeures.objects.get_or_create(
        emploitemps=instance
    )

    # ✅ TOUJOURS synchroniser les heures dues
    calcul.heures_dues = instance.professeur.heure_matiere

    if created:
        calcul.save()
        return

    ancien = instance._ancien_etat
    nouveau = instance.etat

    if ancien == nouveau:
        calcul.save()
        return

    duree = instance.duree_heures

    # ➕ Cours effectué
    if ancien == 'Non effectué' and nouveau == 'Effectué':
        calcul.heures_faites += duree

    # ➖ Annulation
    elif ancien == 'Effectué' and nouveau == 'Non effectué':
        calcul.heures_faites = max(calcul.heures_faites - duree, 0)

    # 🔥 Heures supplémentaires (par professeur)
    calcul.heures_complementaires = max(
        0,
        calcul.heures_faites - calcul.heures_dues
    )

    calcul.date_changement = date.today()
    calcul.save()
