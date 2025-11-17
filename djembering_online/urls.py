from django.urls import path
from .views import (
     home, dashboard_view, 
     admin_view, gestion_heures_view, ajouter_calcul_heures,
     add_autorisation_view, update_autorisation_view, edit_calcul_heures, mettre_a_jour_heures,
     gestions_emploi_view, add_emploi_view, update_emploi, delete_emploi, page_maj_heures,
     gestion_classe_view, add_absence_view, update_absence_view,
     add_professeur_view, update_professeur_view, add_eleves_view, update_eleve_view,
     sections_view, login_view, register_view, logout_view, mon_compte,
)

urlpatterns = [
    path('', home, name='index'),  # index de la page index
    path('dashboard/', dashboard_view, name='dashboard'),  # URL pour le dashboard
    path('admin_view/', admin_view, name='admin_view'),
    path('gestion_heure/', gestion_heures_view, name='gestions_heure'),
    path("gestion_heure/<str:section>/", gestion_heures_view, name="gestions_heure_section"),
    path('sections/<str:section>/', sections_view, name="sections"),
    path('add_heure/', ajouter_calcul_heures, name='add_heure'),
    path('edit_heures/<int:id>/edit/', edit_calcul_heures, name='edit_heures'),
    
     # Route pour la page du template de mise à jour
    path('heures/maj/', page_maj_heures, name='page_maj_heures'),
    # Route pour exécuter la mise à jour
    path('heures/maj/execute/', mettre_a_jour_heures, name='mettre_a_jour_heures'),


    path('gestion_classe/', gestion_classe_view, name='gestion_classe'), 
    path('add_absences/', add_absence_view, name='add_absences'),
    path('update_absence/<str:absence_id>/', update_absence_view, name='update_absence'),
    path('add_professeur', add_professeur_view, name="add_professeur"),
     path('update_professeur/<int:professeur_id>/', update_professeur_view, name='update_professeur'),
    path('add_eleves', add_eleves_view, name="add_eleves"),
    path('update_eleve/<int:eleve_id>/', update_eleve_view, name='update_eleve'),

    path('gestion_emploi/<str:sector>/<str:day>/', gestions_emploi_view, name='gestion_emploi'),
    path('gestion_emploi/<str:sector>/', gestions_emploi_view, name='gestion_emploi'),
    path('gestion_emploi/', gestions_emploi_view, name='gestion_emploi'),
    path('add_emploi/', add_emploi_view, name="add_emploi"),
    path('update_emploi/<int:emploi_id>/', update_emploi, name='update_emploi'),
    path('emploi/<int:emploi_id>/delete/', delete_emploi, name='delete_emploi'),

    path('add_autorisation/', add_autorisation_view, name="add_autorisation"),
    path('update_autorisation/<int:conge_id>/', update_autorisation_view, name='update_autorisation'),

    path('compte/', mon_compte, name="compte"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name="login"),
    path('logout/', logout_view, name="logout"),
]
# add_emploi_view, path('add_emploi', add_emploi_view, name='add_emploi'),