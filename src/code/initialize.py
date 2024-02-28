# -*- coding: utf-8 -*-
"""Initialization of the environment.

Examples:
    >>> Initialize().initialize()
    
    >>> initializer = Initialize()
    >>> initializer.initialize()
"""

import ad
import dns
import share
import filesystem as fs
import constants as cst
import configuration as conf


class Initialize:
    """Initializes the environment (AD and filesystem) from the config.

    Attributes:
        test_shares: Whether to (re)create all shares or not.

        server_dns: DNS of the current server.
        ldap_path: LDAP path of the current server.
        base_ou_ldap: LDAP of the root Organizational Unit.
        teacher_ou_ldap: LDAP of the teacher root Organizational Unit.
        student_ou_ldap: LDAP of the student root Organizational Unit.

        teacher_group_name: Name of the AD group of the teachers.
        student_group_name: Name of the AD group of the students.

        base_dir_path: Path to the base directory of the server.
        teacher_dir_path: Path to the base directory of the teachers.
        student_dir_path: Path to the base directory of the students.

        AP_name: Name of the old teachers group/directory
        AE_name: Name of old students group/directory.

        teacher_ou: Teacher root Organizational Unit.
        student_ou: Student root Organizational Unit.
        teacher_group: Teacher AD group.
        student_group: Student AD group.
        base_dir: Root directory.
        teacher_dir: Root teacher directory.
        student_dir: Root student directory.
        AP_ou: Old teachers Organizational Unit.
        AE_ou: Old students Organizational Unit.
    """

    CONFIG = conf.Config().config_to_dict()

    PYTOR_DIRS = [
        'Nouveaux_Utilisateurs',
        'Nouveaux_Utilisateurs\\ARCHIVES_DES_UTILISATEURS_CREES',
        'Liste_des_Utilisateurs',
        'LOG'
    ]

    def __init__(self) -> None:
        """Initializes the environment from the config.

        Creates variables equal to the config and, through a main function, initializes everything they represent.
        
        Notes:
            The initialize() methods serves to initialize everything. If not used then the environment won't be
            initialized.
        """
        # Test shares.
        # TODO Include a setting for that.
        self.test_shares: bool = True

        # AD variables.
        self.server_dns: str = self.CONFIG['systeme']['domaine_DNS']['value']
        self.ldap_path: str = dns.dns_ldap_path_switcher(self.server_dns)
        self.base_ou_ldap: str = f"ou={self.CONFIG['systeme']['OU']['value']}"
        self.teacher_ou_ldap: str = f"ou={self.CONFIG['professeurs']['OU_professeurs']['value']}," \
                                    f"{self.base_ou_ldap},{self.ldap_path}"
        self.student_ou_ldap: str = f"ou={self.CONFIG['eleves']['OU_eleves']['value']}," \
                                    f"{self.base_ou_ldap},{self.ldap_path}"

        # Groups.
        self.teacher_group_name: str = self.CONFIG['professeurs']['nom_groupeAD_professeurs']['value']
        self.student_group_name: str = self.CONFIG['eleves']['nom_groupeAD_eleves']['value']

        # Directory variables.
        base_dir_drive = self.CONFIG['systeme']['partition_travail']['value']
        base_dir_name = self.CONFIG['systeme']['repertoire_travail']['value']

        self.base_dir_path: str = f'{base_dir_drive}:\\{base_dir_name}'
        self.teacher_dir_path: str = f"{self.base_dir_path}\\{self.CONFIG['professeurs']['repertoire_profs']['value']}"
        self.student_dir_path: str = f"{self.base_dir_path}\\{self.CONFIG['eleves']['repertoire_eleves']['value']}"

        # Archive variables.
        self.AP_name: str = self.CONFIG['fonctionnement']['AP']['value']
        self.AE_name: str = self.CONFIG['fonctionnement']['AE']['value']

        # Objects variables.
        # Initialized in methods.
        self.teacher_ou: ad.adc.ADContainer | None = None
        self.student_ou: ad.adc.ADContainer | None = None
        self.teacher_group: ad.adg.ADGroup | None = None
        self.student_group: ad.adg.ADGroup | None = None
        self.base_dir: fs.Directory | None = None
        self.teacher_dir: fs.Directory | None = None
        self.student_dir: fs.Directory | None = None
        self.AE_ou: ad.adc.ADContainer | None = None
        self.AP_ou: ad.adc.ADContainer | None = None

    def initialize(self) -> None:
        """Initializes everything."""
        # Pytor directories.
        self._create_missing_dirs()

        # Base OU, groups and directory.
        self._create_organizational_units()
        self._create_base_groups()
        self._create_base_dir()

        # Teacher directories.
        self._create_teacher_base_dir()
        self._create_teacher_profile_dir()
        self._create_teacher_subjects_dir()
        self._create_teacher_private_dir()

        # Student directories.
        self._create_student_base_dir()
        self._create_student_profile_dir()
        self._create_student_class_dir()
        self._create_school_shared_dir()
        self._create_student_private_dir()

        # Archives.
        self._create_archive_ou()
        self._create_archive_group()
        self._create_archive_dir()

    def _create_missing_dirs(self) -> None:
        """Creates the directories necessary for the program if they do not exist."""
        for directory in self.PYTOR_DIRS:
            fs.Directory(directory, reset_perms=False)

    def _create_organizational_units(self) -> None:
        """Creates the root Organizational Units."""
        ad.create_ou(self.base_ou_ldap,
                     ad.ou_from_dn(self.ldap_path),
                     {'description': "Utilisateurs de l'établissement"})

        self.teacher_ou = ad.create_ou(self.CONFIG['professeurs']['OU_professeurs']['value'],
                                       ad.ou_from_dn(f'{self.base_ou_ldap},{self.ldap_path}'),
                                       {'description': "Professeurs de l'établissement"})

        self.student_ou = ad.create_ou(self.CONFIG['eleves']['OU_eleves']['value'],
                                       ad.ou_from_dn(f'{self.base_ou_ldap},{self.ldap_path}'),
                                       {'description': "Elèves de l'établissement"})

    def _create_base_groups(self) -> None:
        """Creates the teacher and student AD groups."""
        self.teacher_group = ad.create_group(self.teacher_group_name,
                                             self.teacher_ou,
                                             ad.GroupScope.GLOBAL,
                                             {'description': 'Groupe des professeurs'})

        self.student_group = ad.create_group(self.student_group_name,
                                             self.student_ou,
                                             ad.GroupScope.LOCAL,
                                             {'description': 'Groupe des élèves'})

    def _create_base_dir(self):
        """Creates the root directory."""
        self.base_dir = fs.Directory(self.base_dir_path)

    def _create_teacher_base_dir(self):
        """Creates the teacher root directory."""
        self.teacher_dir = fs.Directory(self.teacher_dir_path)

    def _create_teacher_profile_dir(self) -> None:
        """Creates the teacher profiles root directory."""
        teacher_profile_dir = fs.Directory(f"{self.teacher_dir_path}\\"
                                           f"{self.CONFIG['professeurs']['repertoire_profils_profs']['value']}")

        teacher_profile_dir.give_permission(self.teacher_group_name, cst.Permissions.READ)

        self._create_dir_share(teacher_profile_dir,
                               self.CONFIG['professeurs']['partage_profils_profs']['value'],
                               "Profils des enseignants")

    def _create_teacher_subjects_dir(self):
        """Creates the teacher subjects root directory."""
        subjects_dir = fs.Directory(f"{self.teacher_dir_path}'\\"
                                    f"{self.CONFIG['professeurs']['repertoire_disciplines_profs']['value']}")

        subjects_dir.give_permission(self.teacher_group_name, cst.Permissions.MODIFY)

        self._create_dir_share(subjects_dir,
                               self.CONFIG['professeurs']['partage_disciplines_profs']['value'],
                               "Ressources disciplinaires")

    def _create_teacher_private_dir(self):
        """Creates teacher private directory."""
        private_dir = fs.Directory(f"{self.teacher_dir_path}\\"
                                   f"{self.CONFIG['professeurs']['repertoire_donnees_profs']['value']}")

        private_dir.give_permission(self.teacher_group_name, cst.Permissions.READ)

        self._create_dir_share(private_dir,
                               self.CONFIG['professeurs']['partage_donnees_profs']['value'],
                               "Données des enseignants")

    def _create_student_base_dir(self):
        """Creates student root directory."""
        self.student_dir = fs.Directory(self.student_dir_path)

        # TODO not present in original file for some reason ? Come back later to see why.
        # self.student_dir.give_permission(self.student_group_name, cst.Permissions.READ)

    def _create_student_profile_dir(self):
        """Creates student profiles root directory."""
        student_profile_dir = fs.Directory(f"{self.student_dir_path}\\"
                                           f"{self.CONFIG['eleves']['repertoire_profils_eleves']['value']}")

        student_profile_dir.give_permission(self.student_group_name, cst.Permissions.READ)

        self._create_dir_share(student_profile_dir,
                               self.CONFIG['eleves']['partage_profils_eleves']['value'],
                               "Profils des élèves")

    def _create_student_class_dir(self):
        """Creates class root directory."""
        student_class_dir = fs.Directory(f"{self.student_dir_path}\\"
                                         f"{self.CONFIG['eleves']['repertoire_classes_eleves']['value']}")

        student_class_dir.give_permission(self.teacher_group_name, cst.Permissions.READ)
        student_class_dir.give_permission(self.student_group_name, cst.Permissions.READ)

        self._create_dir_share(student_class_dir,
                               self.CONFIG['eleves']['partage_classes']['value'],
                               "Ressources classes")

    def _create_school_shared_dir(self):
        """Creates a school shared directory."""
        if self.CONFIG['systeme']['repertoire_echange_etablissement_existe']['value'] == 1:
            school_shared_dir = fs.Directory(f"{self.student_dir_path}\\"
                                             f"{self.CONFIG['systeme']['repertoire_echange_etablissement']['value']}")

            school_shared_dir.give_permission(self.teacher_group_name, cst.Permissions.MODIFY_PROTECTED)
            school_shared_dir.give_permission(self.student_group_name, cst.Permissions.MODIFY_PROTECTED)

            self._create_dir_share(school_shared_dir,
                                   self.CONFIG['systeme']['partage_echange_etablissement']['value'],
                                   "Espace commun")

    def _create_student_private_dir(self):
        """Creates a student private directory."""
        private_dir = fs.Directory(f"{self.student_dir_path}\\"
                                   f"{self.CONFIG['eleves']['repertoire_donnees_eleves']['value']}")

        teacher_permissions = self.CONFIG['eleves']['acces_repertoire_eleves']

        if teacher_permissions == 1:
            private_dir.give_permission(self.teacher_group_name, cst.Permissions.READ)
        elif teacher_permissions == 2:
            private_dir.give_permission(self.teacher_group_name, cst.Permissions.MODIFY_PROTECTED)
        private_dir.give_permission(self.student_group_name, cst.Permissions.READ)

        self._create_dir_share(private_dir,
                               self.CONFIG['eleves']['partage_donnees_classes']['value'],
                               "Données des élèves")

    def _create_archive_ou(self):
        """Creates Organizational Units for old teachers and students."""
        self.AP_ou = ad.create_ou(self.AP_name, self.teacher_ou, {'description': self.AP_name})
        self.AE_ou = ad.create_ou(self.AE_name, self.student_ou, {'description': self.AE_name})

    def _create_archive_group(self):
        """Creates AD groups for old teachers and students."""
        group_ap = self.CONFIG['eleves']['nom_groupeAD_classe']['value'].replace('[classe]', self.AP_name)
        group_ae = self.CONFIG['eleves']['nom_groupeAD_classe']['value'].replace('[classe]', self.AE_name)

        ad.create_group(group_ap, self.AP_ou, ad.GroupScope.GLOBAL,
                        {'description': 'Groupe des anciens professeurs'})
        ad.create_group(group_ae, self.AE_ou, ad.GroupScope.GLOBAL,
                        {'description': 'Groupe des anciens élèves'})

    def _create_archive_dir(self):
        """Creates directories or old teachers and students."""
        fs.Directory(f"{self.teacher_dir_path}\\{self.AP_name}")
        fs.Directory(f"{self.student_dir_path}\\{self.AE_name}")

    def _create_dir_share(self, directory: fs.Directory, share_name: str, remark: str) -> None:
        """Creates a share of the directory.

        Args:
            directory: Directory to create a share of.
            share_name: Name of the share.
            remark: Comment on the share.

        Returns:
            None.
        """
        if self.test_shares:
            share.create_share(server=self.server_dns,
                               path=directory.path,
                               share_name=share_name,
                               remark=remark)
