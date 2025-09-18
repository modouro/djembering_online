from datetime import date
from django import forms
from django.contrib.auth import get_user_model
from .models import CongeEmploye, EmploiTemps, Eleves, Professeur, CalculHeures

""" class LoginForm(AuthenticationForm): """
class LoginForm(forms.Form):
    email = forms.EmailField(label='Adresse email', max_length=100, required=True)
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput, required=True)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        # verifie user avec user personnalisé
        user_model = get_user_model()

        try:
            user = user_model.objects.get(email=email)
            if not user.check_password(password):
                raise forms.ValidationError('Mot de passe incorrect')
        except user_model.DoesNotExist:
            raise forms.ValidationError("L'utilisateur n'existe pas avce ce login")
        
        self.user = user
        return cleaned_data

    def get_user(self):
        """ Retourne l'utilisateur authentifié """
        return getattr(self, 'user', None)

class CongeEmployeForm(forms.ModelForm):
    class Meta:
        model = CongeEmploye
        fields = ["professeur", "motif", "date_debut", "date_fin"]
        widgets = {
            'professeur': forms.Select(attrs={'class': 'form-control'}),
            'motif': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        if date_fin and date_debut and date_fin < date_debut:
            raise forms.ValidationError("La date de fin ne peut pas être avant la date de début.")
        return cleaned_data
    
# --------------------------- formulaire emploi du temps 
class EmploiTempsForm(forms.ModelForm):
    class Meta:
        model = EmploiTemps
        fields = ['professeur', 'eleve', 'heure_debut', 'heure_fin', 'jour']
        widgets = {
            'professeur': forms.Select(attrs={'class': 'form-control'}),
            'eleve': forms.Select(attrs={'class': 'form-control'}),
            'heure_debut': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'heure_fin': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'jour': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'professeur': 'Enseignant',
            'eleve': 'Classe/Élève',
            'heure_debut': 'Heure de début',
            'heure_fin': 'Heure de fin',
            'jour': 'Jour',
        }

# ----------------------------- formulaire éléves ---------------------
class ElevesForm(forms.ModelForm):
    class Meta:
        model = Eleves
        fields = ['prenom', 'nom', 'date_naissance', 'lieu_naissance', 'sexe', 'adresse', 'niveau', 'classe']
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sexe': forms.Select(attrs={'class': 'form-control'}),
            'niveau': forms.TextInput(attrs={'class': 'form-control'}),
            'classe': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'lieu_naissance': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'prenom': 'Prénoms',
            'nom': 'Nom',
            'date_naissance': 'Date de naissance',
            'lieu_naissance': 'Lieu de naissance',
            'sexe': 'Sexe',
            'adresse': 'Adresse',
            'niveau': 'Niveau',
            'classe': 'Classe',
        }

    def clean_date_naissance(self):
        date_naissance = self.cleaned_data.get('date_naissance')
        if date_naissance and date_naissance > date.today():
            raise forms.ValidationError("La date de naissance ne peut pas être dans le futur.")
        return date_naissance

# ----------------------------- formulaire professeurs ---------------------
class ProfesseurForm(forms.ModelForm):
    class Meta:
        model = Professeur
        fields = ['prenom', 'nom', 'sexe', 'fonction', 'telephone']
        widgets = {
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
            'sexe': forms.Select(attrs={'class': 'form-control'}),
            'fonction': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Fonction'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Téléphone'}),
        }
        labels = {
            'prenom': 'Prénom',
            'nom': 'Nom',
            'sexe': 'Sexe',
            'fonction': 'Fonction',
            'telephone': 'Téléphone',
        }
