from datetime import  datetime, timedelta, date
from django.forms import ValidationError
from django.db.models import Sum, F, Count, FloatField, Case, When, Value
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST
from django.utils.timezone import now
from django.contrib import messages
from .models import Absence, Administrateur, CalculHeures, EmploiTemps, Eleves, Professeur, CongeEmploye
from django.contrib.auth.hashers import make_password
from .forms import  LoginForm, ElevesForm

def home(request):
  
    context = {
        'message': 'Bienvenue Mamadou',
    }
    return render(request, 'pages/index.html', context)

def dashboard_view(request):
    
    return render(request, 'pages/dashboard.html')

def admin_view(request):
    total_eleves = Eleves.objects.count()
    total_professeurs = Professeur.objects.count()
    total_absences = Absence.objects.count()
    total_conges = CongeEmploye.objects.count()
    total_emplois = EmploiTemps.objects.count()
    
    # Calculer le total des heures
    resultat_aggregation  = EmploiTemps.objects.aggregate(
                                    total=Sum(F('heure_fin') - F('heure_debut'))
                                )

    total_heures = resultat_aggregation.get('total')

    # Conversion en heures
    if total_heures:
        total_heures_en_heures = total_heures.total_seconds() / 3600  # Convertir en heures
        total_heures_format = f"{total_heures_en_heures:.2f} "  # Formater en décimal
    else:
        total_heures_format = "0 heures"
        
    context = {
        "total_eleves": total_eleves,
        "total_professeurs": total_professeurs,
        "total_absences": total_absences,
        "total_conges": total_conges,
        "total_emplois": total_emplois,
        "total_heures": total_heures_format,
    }

    return render(request, 'gestions/admin.html', context)

def get_totals_context():
    return{
        "total_eleves": Eleves.objects.count(),
        "total_professeurs": Professeur.objects.count(),
        }


def get_heures_par_section(section):
    try:
        section_int = int(section)
    except (ValueError, TypeError):
        section_int = None

    # Base queryset
    heures_qs = CalculHeures.objects.select_related(
        "emploitemps", "emploitemps__eleve"
    )

    if section_int is not None:
        heures_qs = heures_qs.filter(emploitemps__eleve__niveau=section_int)

    # Agrégation par niveau + classe
    heures = (
        heures_qs.values("emploitemps__eleve__niveau", "emploitemps__eleve__classe")
        .annotate(
            # 🔸 nombre de classes distinctes
            nombre_classe=Count(
                "emploitemps__eleve__classe", 
                distinct=True
            ),
            # 🔸 sommes totales
            heures_dues=Sum("heures_dues"),
            heures_faites=Sum("heures_faites"),
            heures_complementaires=Sum("heures_complementaires"),
        )
        .annotate(
            ratio=Case(
                When(heures_dues=0, then=Value(0.0)),
                default=F("heures_faites") * 100.0 / F("heures_dues"),
                output_field=FloatField()
            )
        )
        .order_by("emploitemps__eleve__niveau")
    )

    # Totaux par niveau
    totaux_niveau = (
        heures_qs.values("emploitemps__eleve__niveau")
        .annotate(
            total_heures_dues=Sum("heures_dues"),
            total_heures_faites=Sum("heures_faites"),
            total_heures_complementaires=Sum("heures_complementaires"),
        )
        .order_by("emploitemps__eleve__niveau")
    )

    return section, heures, totaux_niveau

def gestion_heures_view(request, section=None):
    if section is None:
        section = request.GET.get("section", 0)

    try:
        section = int(section)
    except (ValueError, TypeError):
        section = 0

    classe = request.GET.get("classe")

    section, heures, totaux_niveau = get_heures_par_section(section)

    # 🔹 Base queryset : professeurs ayant enseigné dans ce niveau
    professeurs = Professeur.objects.filter(
           emploitemps__eleve__niveau=section
       ) 
    # 🔹 On filtre par classe UNIQUEMENT si elle est fournie
    if classe:
        professeurs = professeurs.filter(
            emploitemps__eleve__classe=classe
        )

    professeurs = professeurs.distinct("nom")
    
    return render(request, "gestions/gestion_heure.html", {
        "classe": classe,
        "section": section,
        "heures": heures,
        "totaux_niveau": totaux_niveau,
        "professeurs": professeurs,
    })

def sections_view(request, section=None):
    if section is None:
        """ return redirect("/gestion_heure/0/") """
        return redirect(f"{reverse('gestions_heure')}?section=0")

    section, heures, totaux_niveau = get_heures_par_section(section)

    return render(request, "gestions/gestion_heure.html", {
        "section": section,
        "heures": heures,
        "totaux_niveau": totaux_niveau,
    })


def ajouter_calcul_heures(request):
    # On récupère la section depuis l'URL
    section = request.GET.get("section")

    if request.method == 'POST':
        emploitemps_id = request.POST.get('emploitemps')
        heures_dues_str = request.POST.get('heures_dues', '0')
        heures_faites_str = request.POST.get('heures_faites', '0')

        # Récupération de l'emploi du temps
        emploitemps = get_object_or_404(EmploiTemps, id=emploitemps_id)

        try:
            heures_dues = float(heures_dues_str)
            heures_faites = float(heures_faites_str)
        except ValueError:
            error = "Les heures dues et faites doivent être des nombres valides."
            return render(request, 'gestions/ajouter_calcul_heures.html', {
                'emploitemps': EmploiTemps.objects.filter(eleve__niveau=section),
                'error': error,
                'heures_dues': heures_dues_str,
                'heures_faites': heures_faites_str,
                'selected_emploitemps_id': emploitemps_id,
                'section': section,
            })

        # Création ou mise à jour de CalculHeures
        calcul, created = CalculHeures.objects.update_or_create(
            emploitemps=emploitemps,
            defaults={
                'heures_dues': heures_dues,
                'heures_faites': heures_faites
            }
        )
        messages.success(request, "Heures enregistrées avec succès.")

        # Redirection vers la bonne section après enregistrement
        return redirect(f"{reverse('gestions_heure')}?section={section}")

    # GET : affichage du formulaire (seulement pour la section choisie)
    emploitemps = EmploiTemps.objects.filter(eleve__niveau=section)
    return render(request, 'gestions/ajouter_calcul_heures.html', {
        'emploitemps': emploitemps,
        'section': section
    })


# Page avec le bouton pour lancer la mise à jour

def page_maj_heures(request, section):
    return render(request, 'gestions/maj_heures.html', {'section': section})

def mettre_a_jour_heures(request):
    if request.method == "POST":
        # Exemple : récupérer le niveau automatiquement
        # Ici on prend le niveau d'un "élève en cours" fictif ou défini par l'utilisateur connecté
        # Remplace cette ligne par la logique exacte pour ton application
        niveau_courant = request.user.eleve.niveau if hasattr(request.user, 'eleve') else 3  

        emplois = EmploiTemps.objects.filter(eleve__niveau=niveau_courant)
        count = 0

        for emploi in emplois:
            calcul, created = CalculHeures.objects.get_or_create(emploitemps=emploi)
            duree = emploi.duree_heures

            calcul.heures_dues = duree
            calcul.heures_faites = duree if emploi.etat == "Effectué" else 0
            calcul.heures_complementaires = max(0, calcul.heures_faites - duree)
            calcul.date_changement = date.today()
            calcul.save()
            count += 1

        messages.success(request, f"Niveau {niveau_courant} : {count} emploi(s) mis à jour.")

    return redirect('page_maj_heures')


def edit_calcul_heures(request, calcul_id):
    # Récupération de l'objet CalculHeures à modifier
    calcul = get_object_or_404(CalculHeures, id=calcul_id)

    if request.method == 'POST':
        try:
            heures_dues = float(request.POST.get('heures_dues', calcul.heures_dues))
            heures_faites = float(request.POST.get('heures_faites', calcul.heures_faites))

            calcul.heures_dues = heures_dues
            calcul.heures_faites = heures_faites
            calcul.save()

            return redirect('gestion_heures')  # Nom de ta vue de gestion

        except Exception as e:
            return render(request, 'gestions/edit_heure.html', {
                'calcul': calcul,
                'error': str(e)
            })

    # Si GET → afficher formulaire avec valeurs existantes
    return render(request, 'gestions/edit_heure.html', {
        'calcul': calcul
    })
# ------------------------------------------- debut gestion emploi et fin edit calcul heures -----------------------------------

def gestions_emploi_view(request, section=None, day=None):
    # Liste des secteurs et jours possibles
    sections = ["6", "5", "4", "3"]
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

    # Récupération via GET si présent
    sector_get = request.GET.get("section")
    day_get = request.GET.get("day")

    # Gestion de la section (par défaut = "6")
    if sector_get in sections:
        section = sector_get
    elif section not in sections:
        section = "6"

    if day_get in jours:
        day = day_get
    elif day not in jours:
        # Jour par défaut = jour actuel
        day = datetime.today().strftime('%A')
        # Mapping anglais -> français si nécessaire
        mapping_jours = {
            "Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
            "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi"
        }
        day = mapping_jours.get(day, "Lundi")  # fallback sur Lundi
        

    # Filtrer les emplois
    # emplois = EmploiTemps.objects.filter(eleve__niveau=section, jour=day)
    emplois = EmploiTemps.objects.filter(eleve__niveau=section, jour=day).select_related("professeur", "eleve")

    # Pour chaque emploi, récupérer ses heures et calculer le ratio sécurisé
    heures = []
    for emploi in emplois:
        try:
            calc = CalculHeures.objects.get(emploitemps=emploi)
        except CalculHeures.DoesNotExist:
            # Si aucune entrée, on met tout à zéro
            calc = CalculHeures(emploitemps=emploi, heures_dues=0, heures_faites=0, heures_complementaires=0)

        # Calcul ratio sécurisé
        if calc.heures_dues == 0:
            ratio = 0
        else:
            ratio = round((calc.heures_faites / calc.heures_dues) * 100, 2)

        # Ajouter au dictionnaire pour le template
        heures.append({
            "emploitemps": emploi,
            "heures_dues": calc.heures_dues,
            "heures_faites": calc.heures_faites,
            "heures_complementaires": calc.heures_complementaires,
            "ratio": ratio,
        })

    # Contexte pour le template
    context = {
        "emplois": emplois,
        "heures": heures,            # liste des heures avec ratio calculé
        "section": section,            # secteur actuellement sélectionné
        "sections": sections,          # liste de tous les secteurs
        "jours": jours,              # liste de tous les jours
        "selected_day": day,         # jour actuellement sélectionné
    }

    # Fusion avec tes totaux existants
    total_context = get_totals_context() or {}
    context.update(total_context)

    return render(request, 'gestions/gestions_emploi.html', context)


def add_emploi_view(request):
    professeurs = Professeur.objects.all()
    eleves = Eleves.objects.all()

    # Heure actuelle avec minutes à 00
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    heure_debut_default = now.strftime("%H:%M")
    heure_fin_default = (now + timedelta(hours=1)).strftime("%H:%M")

    if request.method == 'POST':
        heure_debut_str = request.POST.get("heure_debut")
        heure_fin_str = request.POST.get("heure_fin")
        jour = request.POST.get("jour")
        professeur_id = request.POST.get("professeur")
        eleves_id = request.POST.get("eleve")

        # Vérification des champs obligatoires
        if not (professeur_id and eleves_id and heure_debut_str and jour):
            context = {
                "error": "Tous les champs sont obligatoires.",
                "professeurs": professeurs,
                "eleves": eleves,
                "heure_debut_default": heure_debut_default,
                "heure_fin_default": heure_fin_default,
            }
            return render(request, "formulaire/ajouter_emploi.html", context)

        # Conversion de l'heure de début en objet datetime pour manipulation
        heure_debut = datetime.strptime(heure_debut_str, "%H:%M")

        # Si heure_fin non fournie, on l'ajoute automatiquement +1h
        if not heure_fin_str:
            heure_fin = heure_debut + timedelta(hours=1)
        else:
            heure_fin = datetime.strptime(heure_fin_str, "%H:%M")

        professeur = get_object_or_404(Professeur, id=professeur_id)
        eleve = get_object_or_404(Eleves, id=eleves_id)

        # Sauvegarde dans la base
        EmploiTemps.objects.create(
            professeur=professeur,
            eleve=eleve,
            heure_debut=heure_debut.time(),
            heure_fin=heure_fin.time(),
            jour=jour,
        )

        return redirect("gestion_emploi")

    # Si méthode GET → valeurs par défaut
    context = {
        "professeurs": professeurs,
        "eleves": eleves,
        "heure_debut_default": heure_debut_default,
        "heure_fin_default": heure_fin_default,
    }
    return render(request, "formulaire/ajouter_emploi.html", context)


def update_emploi(request, emploi_id):
    emploi = get_object_or_404(EmploiTemps, id=emploi_id)

    if request.method == "POST":
        heure_debut = request.POST.get("heure_debut")
        heure_fin = request.POST.get("heure_fin")
        jour = request.POST.get("jour")
        professeur_id = request.POST.get("professeur")
        eleve_id = request.POST.get("eleve")

        # Validation
        if not all([heure_debut, heure_fin, jour, professeur_id, eleve_id]):
            messages.error(request, "Tous les champs sont requis.")
            return redirect("update_emploi", emploi_id=emploi_id)

        # Mettre à jour les données
        emploi.heure_debut = heure_debut
        emploi.heure_fin = heure_fin
        emploi.jour = jour
        emploi.professeur = get_object_or_404(Professeur, id=professeur_id)
        emploi.eleve = get_object_or_404(Eleves, id=eleve_id)

        try:
            emploi.save()
            messages.success(request, "L'emploi du temps a été mis à jour avec succès.")
            return redirect("gestion_emploi")  # Redirection après succès
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour : {str(e)}")

    professeurs = Professeur.objects.all()
    eleves = Eleves.objects.all()

    return render(request, "modifications/modifier_emploi.html", {
        "emploi": emploi,
        "professeurs": professeurs,
        "eleves": eleves,
    })

def delete_emploi(request, emploi_id):
    # Récupérer l'objet à supprimer
    emploi = get_object_or_404(EmploiTemps, id=emploi_id)

    if request.method == "POST":
        # Si méthode POST, on supprime l'objet
        emploi.delete()
        messages.success(request, "L'emploi du temps a été supprimé avec succès.")
        return redirect('gestion_emploi')  # Remplace 'gestion_emploi' par le nom de ta vue principale

    # Si méthode GET, afficher la page de confirmation
    return render(request, 'modifications/confirm_delete.html', {'emploi': emploi})


# ------------------------------------------- debut gestion classe et fin add emploi -----------------------------------
def update_emploi_et_heures(request):
    """
    Gère la mise à jour de l'état d'un emploi du temps et ajuste les heures faites en conséquence.
    """
    emploi_id = request.POST.get("emploi_id")
    nouvel_etat = request.POST.get("etat")

    emploi = get_object_or_404(EmploiTemps, id=emploi_id)

    # Récupérer ou créer l'objet CalculHeures associé
    calcul_heures, created = CalculHeures.objects.get_or_create(emploitemps=emploi)

    heure_debut = emploi.heure_debut
    heure_fin = emploi.heure_fin
    heures_calculees = calcul_heures.calculer_heures(heure_debut, heure_fin)

    aujourd_hui = datetime.now().date()
    date_dernier_changement = calcul_heures.date_changement

    # Si date différente, on met à jour la date de changement
    if date_dernier_changement != aujourd_hui:
        calcul_heures.date_changement = aujourd_hui

    # Mise à jour des heures faites selon changement d'état
    if emploi.etat != nouvel_etat:
        if emploi.etat == "Effectué" and nouvel_etat != "Effectué":
            # Passage de Effectué à non Effectué => décrémenter heures
            calcul_heures.heures_faites = max(calcul_heures.heures_faites - heures_calculees, 0)
        elif emploi.etat != "Effectué" and nouvel_etat == "Effectué":
            # Passage à Effectué => incrémenter heures
            calcul_heures.heures_faites += heures_calculees

    # Mettre à jour l'état et sauvegarder
    emploi.etat = nouvel_etat
    emploi.save(update_fields=['etat'])
    calcul_heures.save(update_fields=['heures_faites', 'date_changement'])

def paginate_queryset(request, queryset, per_page=2, page_param='page'):
    """
    Fonction utilitaire pour paginer un queryset.
    """
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get(page_param, 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    return page_obj, paginator.num_pages > 1

def gestion_classe_view(request):
    # Gestion du POST : mise à jour état + heures
    if request.method == "POST" and "emploi_id" in request.POST and "etat" in request.POST:
        update_emploi_et_heures(request)
        return redirect('gestion_classe')
    
    niveau_filtre = request.GET.get("niveau")

    # Récupération et pagination des élèves
    eleves = Eleves.objects.all().order_by('id')

    if niveau_filtre:
        eleves = eleves.filter(niveau=niveau_filtre)

    eleves_page_obj, afficher_pagination_eleve = paginate_queryset(request, eleves, per_page=2, page_param='page_eleves')

    # Récupération et pagination des professeurs
    professeurs = Professeur.objects.all().order_by('id')
    professeur_page_obj, afficher_pagination_professeur = paginate_queryset(request, professeurs, per_page=2, page_param='page_professeur')

    # Récupération et pagination des absences avec jointures
    absences = Absence.objects.select_related('eleve', 'emploitemps').all().order_by('-emploitemps__jour', '-emploitemps__heure_debut')
    absences_page_obj, afficher_pagination_absent = paginate_queryset(request, absences, per_page=2)

    jours_valides_dict = dict(EmploiTemps._meta.get_field('jour').choices)
    jours_valides = jours_valides_dict.values()
    jour_actuel_en = datetime.now().strftime('%A')
    # Traduction jour anglais -> code interne (ex: 'Monday' -> 'Lundi')
    jour_actuel_fr = {v: k for k, v in jours_valides_dict.items()}.get(jour_actuel_en)

    niveau_selectionne = request.GET.get("niveau")
    jour_selectionne = request.GET.get("jour")

    # Si niveau sélectionné et valide, récupérer les jours où ce niveau a des emplois
    if niveau_selectionne and niveau_selectionne.isdigit():
        # Récupérer les jours distincts pour ce niveau
        jours_niveau_qs = EmploiTemps.objects.filter(
            eleve__niveau=int(niveau_selectionne)
        ).values_list('jour', flat=True).distinct()

        # Construire un dict jours valable pour ce niveau
        jours_valides_filtrés = {
            jour: jours_valides_dict[jour]
            for jour in jours_niveau_qs if jour in jours_valides_dict
        }
    else:
        # Pas de niveau sélectionné => tous les jours
        jours_valides_filtrés = jours_valides_dict

    # Si jour_selectionne absent ou invalide, on peut prendre le premier jour valide
    if not jour_selectionne or jour_selectionne not in jours_valides_filtrés:
        jour_selectionne = next(iter(jours_valides_filtrés), None)

    # Filtrer les emplois par niveau et jour
    emplois = EmploiTemps.objects.all()
    if niveau_selectionne and niveau_selectionne.isdigit():
        emplois = emplois.filter(eleve__niveau=int(niveau_selectionne))

    if jour_selectionne in jours_valides_filtrés:
        emplois = emplois.filter(jour=jour_selectionne)
    else:
        emplois = EmploiTemps.objects.none()
    
    presences_page_obj, afficher_pagination = paginate_queryset(request, emplois, per_page=2)

    # Construire la liste des niveaux (inchangé)
    niveaux_raw = EmploiTemps.objects.values_list('eleve__niveau', flat=True).distinct().order_by('eleve__niveau')
    niveaux = [(n, f"Classe {n}") for n in niveaux_raw if n is not None]

    # Récupération de totaux (supposée exister dans ton code)
    total_context = get_totals_context() or {}
    
    context = {
        'eleves_page_obj': eleves_page_obj,
        'afficher_pagination_eleve': afficher_pagination_eleve,
        'professeur_page_obj': professeur_page_obj,
        'afficher_pagination_professeur': afficher_pagination_professeur,
        'absences_page_obj': absences_page_obj,
        'afficher_pagination_absent': afficher_pagination_absent,
        'presences_page_obj': presences_page_obj,
        'afficher_pagination': afficher_pagination,
        'jour': jour_selectionne,
        'jours_valides': jours_valides_filtrés,  # <-- Ici on envoie la liste filtrée des jours
        'niveau_param': niveau_selectionne,
        'niveaux': niveaux,
        'professeurs': professeurs,
        'emplois': emplois,
        'niveau_filtre': niveau_filtre,
    }
    context.update(total_context)

    return render(request, 'gestions/gestion_classes.html', context)

# ------------------------------------------- fin et debut add professeur -----------------------------------
""" @login_required(login_url="login") """
def add_professeur_view(request):
    if request.method == 'POST':
        prenom = request.POST.get('prenom')
        nom = request.POST.get('nom')
        sexe = request.POST.get('sexe')
        fonction = request.POST.get('fonction')
        telephone = request.POST.get('telephone')
        heure_matiere = request.POST.get('heure_matiere')

        # Validation basique
        if not (prenom and nom and sexe and fonction and telephone and heure_matiere):
            messages.error(request, "Veuillez remplir tous les champs.")
            return redirect('gestion_classe')  # Remplacez par l'URL de votre page

        # Création du professeur
        Professeur.objects.create(
            prenom=prenom,
            nom=nom,
            sexe=sexe,
            fonction=fonction,
            telephone=telephone,
            heure_matiere=heure_matiere
        )
        messages.success(request, "Professeur ajouté avec succès !")
        return redirect('gestion_classe')  # Remplacez par l'URL de votre page
    else:
        messages.error(request, "Méthode non autorisée.")
        return redirect('gestion_classe')  # Remplacez par l'URL de votre page
    
def update_professeur_view(request, professeur_id):
    professeur = get_object_or_404(Professeur, id=professeur_id)

    if request.method == 'POST':
        prenom = request.POST.get('prenom')
        nom = request.POST.get('nom')
        sexe = request.POST.get('sexe')
        fonction = request.POST.get('fonction')
        telephone = request.POST.get('telephone')
        heure_matiere = request.POST.get('heure_matiere')

        # Validation basique
        if not (prenom and nom and sexe and fonction and telephone and heure_matiere):
            messages.error(request, "Veuillez remplir tous les champs.")
            return redirect('edit_professeur', professeur_id=professeur_id)

        # Mise à jour du professeur
        professeur.prenom = prenom
        professeur.nom = nom
        professeur.sexe = sexe
        professeur.fonction = fonction
        professeur.telephone = telephone
        professeur.heure_matiere = heure_matiere
        professeur.save()

        messages.success(request, "Professeur modifié avec succès !")
        return redirect('gestion_classe')  # Remplacez par l'URL de votre page
    else:
        context = {
            'professeur': professeur
        }
        return render(request, 'modifications/modifier_prof.html', context)
# ----------------------------- ajouter les éléves dans la base de données ---------
def add_eleves_view(request):
    if request.method == "POST":
        form = ElevesForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Élève ajouté avec succès.")
            return redirect('gestion_classe')
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
    else:
        form = ElevesForm()
    return render(request, "gestions/gestion_classes.html", {"form": form})

def update_eleve_view(request, eleve_id):
    # Récupérer l'élève ou retourner une erreur 404
    eleve = get_object_or_404(Eleves, id=eleve_id)

    if request.method == 'POST':
        # Récupérer les données du formulaire
        prenom = request.POST.get('prenom')
        nom = request.POST.get('nom')
        date_naissance = request.POST.get('date_naissance')
        lieu_naissance = request.POST.get('lieu_naissance')
        sexe = request.POST.get('sexe')
        adresse = request.POST.get('adresse')
        niveau = request.POST.get('niveau')
        classe = request.POST.get('clasee')

        # Validation de base
        if not all([prenom, nom, date_naissance, lieu_naissance, sexe, adresse, niveau]):
            messages.error(request, "Veuillez remplir tous les champs.")
            return redirect('update_eleve', eleve_id=eleve.id)

        try:
            # Validation spécifique
            if date_naissance and now().date() < now().strptime(date_naissance, "%Y-%m-%d").date():
                raise ValidationError("La date de naissance ne peut pas être dans le futur.")
            
            # Mise à jour des informations de l'élève
            eleve.prenom = prenom
            eleve.nom = nom
            eleve.date_naissance = date_naissance
            eleve.lieu_naissance = lieu_naissance
            eleve.sexe = sexe
            eleve.adresse = adresse
            eleve.niveau = int(niveau)
            eleve.classe = classe
            eleve.save()

            messages.success(request, "Élève modifié avec succès.")
            return redirect('gestion_classe')  # Remplacez par l'URL de votre page de gestion de classe

        except ValidationError as e:
            messages.error(request, e.message)
            return redirect('update_eleve', eleve_id=eleve.id)

    # Si la méthode est GET, pré-remplir les données de l'élève
    context = {
        'eleve': eleve,
    }
    return render(request, 'modifications/modif_eleve.html', context)
#----------------------------------------------------------------------
def add_absence_view(request):
    if request.method == 'POST':
        eleve_id = request.POST.get('eleve')
        emploitemps_id = request.POST.get('emploitemps')
        justification = request.POST.get('justification', 'Non justifiée')  # Défaut à "Non justifiée"
        professeur_id = request.POST.get('professeur')  # Récupération du professeur

        if not eleve_id or not emploitemps_id or not justification  or not professeur_id:
            messages.error(request, "Tous les champs sont obligatoires.")
            return redirect('gestion_classe')  # Replacez par l'URL ou nom de vue approprié

        try:
            eleve = get_object_or_404(Eleves, id=eleve_id)
            emploitemps = get_object_or_404(EmploiTemps, id=emploitemps_id)
            professeur = get_object_or_404(Professeur, id=professeur_id)

            # Créer l'absence
            Absence.objects.create(
                eleve=eleve,
                emploitemps=emploitemps,
                justification=justification,
                professeur=professeur
            )
            messages.success(request, "Absence ajoutée avec succès.")
            return redirect('gestion_classe')  # URL de redirection après succès
        
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
            return redirect('gestion_classe')

    return redirect('gestion_classe')
    
def update_absence_view(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)

    if request.method == 'POST':
        eleve_id = request.POST.get('eleve')
        emploitemps_id = request.POST.get('emploitemps')
        justification = request.POST.get('justification', 'Non justifiée')  # Défaut à "Non justifiée"
        professeur_id = request.POST.get('professeur')

        # Validation des champs
        if not eleve_id or not emploitemps_id or not justification or not professeur_id:
            messages.error(request, "Tous les champs sont obligatoires.")
            return redirect('update_absence', absence_id=absence.id)

        try:
            eleve = get_object_or_404(Eleves, id=eleve_id)
            emploitemps = get_object_or_404(EmploiTemps, id=emploitemps_id)
            professeur = get_object_or_404(Professeur, id=professeur_id)

            # Mettre à jour les données de l'absence
            absence.eleve = eleve
            absence.emploitemps = emploitemps
            absence.justification = justification
            absence.professeur = professeur
            absence.save()

            messages.success(request, "Absence mise à jour avec succès.")
            return redirect('gestion_classe')  # URL de redirection après succès
        
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
            return redirect('update_absence', absence_id=absence.id)
        
         # Préparer les données pour afficher dans le formulaire
    eleves = Eleves.objects.all()
    professeurs = Professeur.objects.all()
    emplois = EmploiTemps.objects.all()

    context = {
        'absence': absence,
        'eleves': eleves,
        'professeurs': professeurs,
        'emplois': emplois,
    }
        
    return render(request, 'modifications/modifier_absence.html', context)
#----------------------------------------------------------------------  
def add_autorisation_view(request):
    if request.method == 'POST':
        professeur_id = request.POST.get('professeur')
        motif = request.POST.get('motif')
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin')

        # Création et validation des données
        CongeEmploye.objects.create(
            professeur_id=professeur_id,
            motif=motif,
            date_debut=date_debut,
            date_fin=date_fin,
        )
        return redirect('add_autorisation')  # Rediriger après enregistrement

        # Préparer les données pour le template
    professeurs = Professeur.objects.filter(sexe='F')  # Femmes uniquement
    conges = CongeEmploye.objects.select_related('professeur').all()  # Récupérer tous les congés

    context = {
        "professeurs": professeurs,
        "conges": conges,
    }
        
    return render(request, 'gestions/gestions_autorisation.html', context)
def update_autorisation_view(request, conge_id):
    # Récupérer le congé existant ou retourner une erreur 404 s'il n'existe pas
    conge = get_object_or_404(CongeEmploye, id=conge_id)

    if request.method == 'POST':
        professeur_id = request.POST.get('professeur')
        motif = request.POST.get('motif')
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin')

        # Mise à jour des champs du congé
        conge.professeur_id = professeur_id
        conge.motif = motif
        conge.date_debut = date_debut
        conge.date_fin = date_fin
        conge.save()  # Sauvegarder les modifications

        return redirect('add_autorisation')  # Rediriger vers la liste des congés après mise à jour

    # Préparer les données pour le template
    professeurs = Professeur.objects.filter(sexe='F')  # Femmes uniquement

    context = {
        "conge": conge,
        "professeurs": professeurs,
    }

    return render(request, 'modification_conge/modifie_conge.html', context)
# -------------------------- register d'inscription ------------------------
def register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        fonction = request.POST.get('fonction')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # éviter les doublon en validant les emails
        if Administrateur.objects.filter(email=email).exists():
            messages.error(request, "l'email est dèjà utilisé ")
            return render(request, 'compte/register.html')
        
        admin = Administrateur(
            prenoms=first_name,
            nom =last_name,
            fonction=fonction,
            email=email,
            password = make_password(password), # mot de passe hachez
            is_staff=True  # il nous permet de donner les permissions du staff
        )
        # admin.password = make_password(password) # mot de passe hachez
        admin.save()

        messages.success(request, "compte crée avec succès. ")
        return redirect('login')
    return render(request, 'compte/register.html')
@login_required(login_url="login")
def mon_compte(request):
    user = request.user

    # Récupérer les données de l'administrateur connecté
    admin = Administrateur.objects.filter(email=user.email).first()

    if request.method == 'POST':
        # Mise à jour des champs de l'administrateur
        if admin:  # Vérifiez si un administrateur existe pour cet utilisateur
            admin.prenoms = request.POST.get('prenom', admin.prenoms)
            admin.nom = request.POST.get('nom', admin.nom)
            admin.fonction = request.POST.get('fonction', admin.fonction)
            admin.adresse = request.POST.get('adresse', admin.adresse)
            admin.telephone = request.POST.get('telephone', admin.telephone)

            # Sauvegarder l'administrateur
            admin.save()

        # Mise à jour de l'email de l'utilisateur si nécessaire
        new_email = request.POST.get('email', user.email)
        if new_email != user.email:
            user.email = new_email

        # Mise à jour du mot de passe si nécessaire
        new_password = request.POST.get('password', None)
        if new_password:
            user.set_password(new_password)  # Changer le mot de passe de manière sécurisée

        # Sauvegarder l'utilisateur
        user.save()

        # Message de succès
        messages.success(request, "Votre compte a été mis à jour avec succès.")

        # Rediriger vers la page du compte
        return redirect("compte")  # Changez ceci selon la vue vers laquelle vous voulez rediriger

    # Passer les informations au contexte
    context = {
        'prenom': admin.prenoms if admin else user.first_name,
        'nom': admin.nom if admin else user.last_name,
        'fonction': admin.fonction if admin else '',
        'adresse': admin.adresse if admin else "",
        'telephone': admin.telephone if admin else "",
        'email': admin.email if admin else user.email,
    }

    return render(request, 'gestions/compte_admin.html', context)
# -----------------------------login view ----------------------------
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            #authentified user
            user_model = get_user_model()
            try:
                # Récupére user par email
                user = user_model.objects.get(email=email)

                # si l'utilisateur existe et que les identifiants sont corrects 
                if user.check_password(password):
                    login(request, user)
                    messages.success(request, "connexion réussie ! ")
                    return redirect('dashboard') # je vais vers la page d'accueil
                else:
                    messages.error(request, "Mot de passe incorrect")
            except user_model.DoesNotExist:
                messages.error(request, "L'utilisateur avec ce mail n'existe pas.")
        else:
            messages.error(request, "identifiants incorrects")
    else:
        form = LoginForm()
    
    return render(request, 'compte/login.html', {'form': form}) 
# ------------------- deconexion ------------------------------------
def logout_view(request):
    logout(request) # déconnexion
    return redirect('login') # redirigez vers la page login
