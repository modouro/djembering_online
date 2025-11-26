from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date, datetime, time
from django.utils.timezone import now
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission

class AdminManager(BaseUserManager):
    def create_user(self, email, prenoms, nom, mot_de_passe=None, **extra_fields):
        if not email:
            raise ValueError(_("L'adresse email est obligatoire"))
        email = self.normalize_email(email)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        user = self.model(email=email, prenoms=prenoms, nom=nom, **extra_fields)
        user.set_password(mot_de_passe)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, prenoms, nom, mot_de_passe=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, prenoms, nom, mot_de_passe, **extra_fields)

class Administrateur(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    prenoms = models.CharField(max_length=100, verbose_name=_("Prénoms"))
    nom = models.CharField(max_length=100, verbose_name=_("Nom"))
    fonction = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Fonction"))
    adresse = models.CharField(max_length=255, verbose_name=_("Adresse"))
    telephone = models.CharField(max_length=10, verbose_name=_("Téléphone"))
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, related_name="administrateur_groups", blank=True, verbose_name=_("Groupes"))
    user_permissions = models.ManyToManyField(Permission, related_name="administrateur_permissions", blank=True, verbose_name=_("Permissions"))

    objects = AdminManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['prenoms', 'nom']

    def __str__(self):
        return f"{self.prenoms} {self.nom} - {self.email}"

    def clean(self):
        if not self.telephone.isdigit() or len(self.telephone) != 10:
            raise ValidationError(_("Le numéro de téléphone doit contenir exactement 10 chiffres."))

class Eleves(models.Model):
    SEX_CHOICES = [
        ('M', _('Masculin')),
        ('F', _('Féminin')),
    ]
    prenom = models.CharField(max_length=150, verbose_name=_("Prénoms"))
    nom = models.CharField(max_length=100, verbose_name=_("Nom"))
    date_naissance = models.DateField(verbose_name=_("Date de naissance"))
    lieu_naissance = models.CharField(max_length=150, verbose_name=_("Lieu de naissance"))
    sexe = models.CharField(max_length=1, choices=SEX_CHOICES, verbose_name=_("Sexe"))
    adresse = models.CharField(max_length=150, verbose_name=_("Adresse"))
    niveau = models.IntegerField(
    verbose_name=_("Niveau"),
    validators=[
        MinValueValidator(3),
        MaxValueValidator(6)  # selon ton système éducatif, adapte cette limite
    ]
    )
    classe = models.CharField(max_length=1, verbose_name=_("Classe"), blank=True, null=True)
    # exemple : "A", "B", "C"

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def age(self):
        today = date.today()
        return today.year - self.date_naissance.year - (
            (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
        )

    def clean(self):
        if self.date_naissance > now().date():
            raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))

class Professeur(models.Model):
    SEX_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    prenom = models.CharField(max_length=150, verbose_name=_("Prénoms"))
    nom = models.CharField(max_length=100, verbose_name=_("Nom"))
    sexe = models.CharField(max_length=1, choices=SEX_CHOICES, verbose_name=_("Sexe"), db_index=True)
    fonction = models.CharField(max_length=100, verbose_name=_("Fonction"))
    telephone = models.CharField(max_length=10, verbose_name=_("Téléphone"))
    heure_matiere = models.IntegerField(
    default=0,
    verbose_name=_("Heures de matière"),
    validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.fonction} {self.heure_matiere} h"

    def clean(self):
        if not self.telephone.isdigit() or len(self.telephone) != 10:
            raise ValidationError(_("Le numéro de téléphone doit contenir exactement 10 chiffres."))

class EmploiTemps(models.Model):
    professeur = models.ForeignKey(Professeur, verbose_name=_("Professeur"), on_delete=models.CASCADE)
    eleve = models.ForeignKey(Eleves, verbose_name=_("Élève"), on_delete=models.CASCADE)
    heure_debut = models.TimeField(verbose_name=_("Heure de début"))
    heure_fin = models.TimeField(verbose_name=_("Heure de fin"))
    jour = models.CharField(max_length=16, choices=[
        ('Lundi', _('Lundi')),
        ('Mardi', _('Mardi')),
        ('Mercredi', _('Mercredi')),
        ('Jeudi', _('Jeudi')),
        ('Vendredi', _('Vendredi')),
        ('Samedi', _('Samedi')),
        ('Dimanche', _('Dimanche')),
    ], verbose_name=_("Jour"))
    etat = models.CharField(
        max_length=12,
        choices=[('Non effectué', 'Non effectué'), ('Effectué', 'Effectué')],
        default='Non effectué',
        verbose_name=_("État"),
    )

    def __str__(self):
        return f"{self.professeur} - {self.eleve} ({self.heure_debut} - {self.heure_fin} - {self.etat})"

    @property
    def niveau_eleve(self):
        return self.eleve.niveau

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['professeur', 'jour', 'heure_debut', 'heure_fin'], name='unique_emploi_temps')
        ]

    @property
    def duree_heures(self):
        debut = datetime.combine(datetime.today(), self.heure_debut)
        fin = datetime.combine(datetime.today(), self.heure_fin)
        return (fin - debut).seconds / 3600

    def save(self, *args, **kwargs):
        # Vérifier si l'objet existe déjà (donc mise à jour)
        if self.pk:
            ancien = EmploiTemps.objects.get(pk=self.pk)
            etat_avant = ancien.etat
            etat_apres = self.etat

            if etat_avant != etat_apres:
                try:
                    calcul = CalculHeures.objects.get(emploitemps=self)
                    duree = self.duree_heures

                    if etat_avant == 'Non effectué' and etat_apres == 'Effectué':
                        calcul.heures_faites += duree
                        calcul.save()
                    elif etat_avant == 'Effectué' and etat_apres == 'Non effectué':
                        calcul.heures_faites -= duree
                        if calcul.heures_faites < 0:
                            calcul.heures_faites = 0
                        calcul.save()
                except CalculHeures.DoesNotExist:
                    pass  # Aucun calcul encore associé, on ne fait rien

        super().save(*args, **kwargs)

class Absence(models.Model):
    eleve = models.ForeignKey(Eleves, on_delete=models.CASCADE, related_name="absences") 
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE, related_name="professeur", default=1)
    emploitemps = models.ForeignKey(EmploiTemps, on_delete=models.CASCADE, related_name="emploi")
    justification = models.CharField(
        max_length=25,
        choices=[('Non justifiée', 'Non justifiée'), ('justifiée', 'justifiée')],
        default='Non justifiée',
        verbose_name=_("Justification"),
    )

    def __str__(self):
        return f"Absence de {self.eleve} ({self.emploitemps}) - {self.justification} - {self.professeur}"

class CongeEmploye(models.Model):  
    professeur = models.ForeignKey(
        Professeur, 
        on_delete=models.CASCADE, 
        limit_choices_to={'sexe': 'F'}, 
        verbose_name=_("Professeur (Femmes uniquement)")
    )
    motif = models.TextField(verbose_name=_("Motif du congé"))
    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_fin = models.DateField(verbose_name=_("Date de fin"))
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    def __str__(self):
        return f"{self.professeur} - {self.date_debut} à {self.date_fin}"

    def clean(self):
        if self.date_fin < self.date_debut:
            raise ValidationError(_("La date de fin ne peut pas être avant la date de début."))

class CalculHeures(models.Model):
    emploitemps = models.OneToOneField(EmploiTemps, on_delete=models.CASCADE, verbose_name=_("Emploi du temps"))
    heures_dues = models.FloatField(default=0, verbose_name=_("Heures dues"))
    heures_faites = models.FloatField(default=0, verbose_name=_("Heures faites"))
    heures_complementaires = models.FloatField(default=0, verbose_name=_("Heures supplémentaires"))
    date_changement = models.DateField(null=True, blank=True, verbose_name=_("Date du dernier changement"))

    def calculer_heures(self, heure_debut, heure_fin):
        """
        Calcule la durée en heures entre l'heure de début et l'heure de fin.
        """
        if isinstance(heure_debut, time):
            heure_debut = heure_debut.strftime("%H:%M")
        if isinstance(heure_fin, time):
            heure_fin = heure_fin.strftime("%H:%M")

        format_heure = "%H:%M"
        debut = datetime.strptime(heure_debut, format_heure)
        fin = datetime.strptime(heure_fin, format_heure)
        difference = (fin - debut).total_seconds() / 3600
        return round(difference, 2)

    def __str__(self):
        return (
            f"{self.emploitemps} - Dues: {self.heures_dues},"
            f"Faites: {self.heures_faites}, Supplémentaires: {self.heures_complementaires}"
        )
   