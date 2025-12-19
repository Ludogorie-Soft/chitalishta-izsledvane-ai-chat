"""Semantic transformation service - converts DB data to Bulgarian narrative text."""
from typing import Optional


class SemanticTransformationService:
    """Service for transforming raw database data into Bulgarian narrative text."""

    def __init__(self):
        """Initialize the semantic transformation service."""
        pass

    def transform_chitalishte_to_text(self, chitalishte_data: dict) -> str:
        """
        Transform Chitalishte data dictionary to Bulgarian narrative text.

        Args:
            chitalishte_data: Dictionary containing Chitalishte data

        Returns:
            Bulgarian narrative text describing the Chitalishte
        """
        parts = []

        # Basic information
        if chitalishte_data.get("name"):
            parts.append(f"Читалище: {chitalishte_data['name']}")

        if chitalishte_data.get("registration_number"):
            parts.append(
                f"Регистрационен номер: {chitalishte_data['registration_number']}"
            )

        # Location information
        location_parts = []
        if chitalishte_data.get("region"):
            location_parts.append(f"област {chitalishte_data['region']}")
        if chitalishte_data.get("municipality"):
            location_parts.append(f"община {chitalishte_data['municipality']}")
        if chitalishte_data.get("town"):
            location_parts.append(f"град {chitalishte_data['town']}")
        if chitalishte_data.get("address"):
            location_parts.append(f"адрес: {chitalishte_data['address']}")

        if location_parts:
            parts.append(f"Локация: {', '.join(location_parts)}")

        # Status
        if chitalishte_data.get("status"):
            parts.append(f"Статус: {chitalishte_data['status']}")

        # Contact information
        contact_parts = []
        if chitalishte_data.get("chairman"):
            contact_parts.append(f"председател: {chitalishte_data['chairman']}")
        if chitalishte_data.get("secretary"):
            contact_parts.append(f"секретар: {chitalishte_data['secretary']}")
        if chitalishte_data.get("phone"):
            contact_parts.append(f"телефон: {chitalishte_data['phone']}")
        if chitalishte_data.get("email"):
            contact_parts.append(f"имейл: {chitalishte_data['email']}")

        if contact_parts:
            parts.append(f"Контакти: {', '.join(contact_parts)}")

        # Additional information
        if chitalishte_data.get("bulstat"):
            parts.append(f"БУЛСТАТ: {chitalishte_data['bulstat']}")

        if chitalishte_data.get("chitalishta_url"):
            parts.append(f"Уебсайт на читалището: {chitalishte_data['chitalishta_url']}")

        if chitalishte_data.get("url_to_libraries_site"):
            parts.append(
                f"Връзка към сайта на библиотеките: {chitalishte_data['url_to_libraries_site']}"
            )

        return ". ".join(parts) + "."

    def transform_information_card_to_text(
        self, card_data: dict, chitalishte_name: Optional[str] = None
    ) -> str:
        """
        Transform InformationCard data dictionary to Bulgarian narrative text.

        Args:
            card_data: Dictionary containing InformationCard data
            chitalishte_name: Optional name of the Chitalishte for context

        Returns:
            Bulgarian narrative text describing the InformationCard
        """
        parts = []

        # Year context
        year = card_data.get("year")
        if year:
            parts.append(f"Данни за {year} година")
        if chitalishte_name:
            parts.append(f"за читалище {chitalishte_name}")

        # Membership information
        membership_parts = []
        if card_data.get("total_members_count") is not None:
            count = int(card_data["total_members_count"])
            membership_parts.append(
                f"общо {self._format_number(count, 'член', 'члена', 'члена')}"
            )
        if card_data.get("new_members") is not None:
            count = int(card_data["new_members"])
            membership_parts.append(
                f"{self._format_number(count, 'нов', 'нови', 'нови')} {self._format_number(count, 'член', 'члена', 'члена')}"
            )
        if card_data.get("membership_applications") is not None:
            count = int(card_data["membership_applications"])
            membership_parts.append(
                f"{self._format_number(count, 'кандидатура', 'кандидатури', 'кандидатури')} за членство"
            )
        if card_data.get("rejected_members") is not None:
            count = int(card_data["rejected_members"])
            membership_parts.append(
                f"{self._format_number(count, 'отказан', 'отказани', 'отказани')} {self._format_number(count, 'член', 'члена', 'члена')}"
            )

        if membership_parts:
            parts.append(f"Членство: {', '.join(membership_parts)}")

        # Employees
        employee_parts = []
        if card_data.get("employees_count") is not None:
            count = float(card_data["employees_count"])
            employee_parts.append(
                f"{self._format_decimal(count)} {self._format_number(int(count), 'служител', 'служители', 'служители')}"
            )
        if card_data.get("employees_with_higher_education") is not None:
            count = int(card_data["employees_with_higher_education"])
            employee_parts.append(
                f"{self._format_number(count, 'с', 'с', 'с')} висше образование: {count}"
            )
        if card_data.get("employees_specialized") is not None:
            count = int(card_data["employees_specialized"])
            employee_parts.append(
                f"{self._format_number(count, 'специализиран', 'специализирани', 'специализирани')}: {count}"
            )
        if card_data.get("supporting_employees") is not None:
            count = int(card_data["supporting_employees"])
            employee_parts.append(
                f"{self._format_number(count, 'поддържащ', 'поддържащи', 'поддържащи')} персонал: {count}"
            )

        if employee_parts:
            parts.append(f"Персонал: {', '.join(employee_parts)}")

        # Subsidiary count
        if card_data.get("subsidiary_count") is not None:
            count = float(card_data["subsidiary_count"])
            parts.append(
                f"Субсидирана бройка: {self._format_decimal(count)} {self._format_number(int(count), 'бройка', 'бройки', 'бройки')}"
            )

        # Cultural activities
        activity_parts = []
        if card_data.get("folklore_formations") is not None:
            count = int(card_data["folklore_formations"])
            activity_parts.append(
                f"{self._format_number(count, 'фолклорна', 'фолклорни', 'фолклорни')} формация"
            )
        if card_data.get("theatre_formations") is not None:
            count = int(card_data["theatre_formations"])
            activity_parts.append(
                f"{self._format_number(count, 'театрална', 'театрални', 'театрални')} формация"
            )
        if card_data.get("vocal_groups") is not None:
            count = int(card_data["vocal_groups"])
            activity_parts.append(
                f"{self._format_number(count, 'вокална', 'вокални', 'вокални')} група"
            )
        if card_data.get("dancing_groups") is not None:
            count = int(card_data["dancing_groups"])
            activity_parts.append(
                f"{self._format_number(count, 'танцова', 'танцови', 'танцови')} група"
            )
        if card_data.get("modern_ballet") is not None:
            count = int(card_data["modern_ballet"])
            activity_parts.append(
                f"{self._format_number(count, 'модерна', 'модерни', 'модерни')} балетна формация"
            )
        if card_data.get("amateur_arts") is not None:
            count = int(card_data["amateur_arts"])
            activity_parts.append(
                f"{self._format_number(count, 'любителска', 'любителски', 'любителски')} художествена формация"
            )

        if activity_parts:
            parts.append(f"Културни формации: {', '.join(activity_parts)}")

        # Clubs and activities
        club_parts = []
        if card_data.get("kraeznanie_clubs") is not None:
            count = int(card_data["kraeznanie_clubs"])
            club_parts.append(
                f"{self._format_number(count, 'краезначески', 'краезначески', 'краезначески')} клуб"
            )
        if card_data.get("language_courses") is not None:
            count = int(card_data["language_courses"])
            club_parts.append(
                f"{self._format_number(count, 'езиков', 'езикови', 'езикови')} курс"
            )
        if card_data.get("workshops_clubs_arts") is not None:
            count = int(card_data["workshops_clubs_arts"])
            club_parts.append(
                f"{self._format_number(count, 'ателие', 'ателиета', 'ателиета')} по изкуства"
            )
        if card_data.get("other_clubs") is not None:
            count = int(card_data["other_clubs"])
            club_parts.append(
                f"{self._format_number(count, 'друг', 'други', 'други')} клуб"
            )

        if club_parts:
            parts.append(f"Клубове и курсове: {', '.join(club_parts)}")

        # Library activity
        if card_data.get("library_activity") is not None:
            count = int(card_data["library_activity"])
            parts.append(
                f"Библиотечна дейност: {self._format_number(count, 'активност', 'активности', 'активности')}"
            )

        # Museum collections
        if card_data.get("museum_collections") is not None:
            count = int(card_data["museum_collections"])
            parts.append(
                f"Музейни колекции: {self._format_number(count, 'колекция', 'колекции', 'колекции')}"
            )

        # Participation
        participation_parts = []
        if card_data.get("participation_in_events") is not None:
            count = int(card_data["participation_in_events"])
            participation_parts.append(
                f"{self._format_number(count, 'участие', 'участия', 'участия')} в събития"
            )
        if card_data.get("participation_in_trainings") is not None:
            count = int(card_data["participation_in_trainings"])
            participation_parts.append(
                f"{self._format_number(count, 'участие', 'участия', 'участия')} в обучения"
            )
        if card_data.get("projects_participation_leading") is not None:
            count = int(card_data["projects_participation_leading"])
            participation_parts.append(
                f"{self._format_number(count, 'водещ', 'водещи', 'водещи')} проекти"
            )
        if card_data.get("projects_participation_partner") is not None:
            count = int(card_data["projects_participation_partner"])
            participation_parts.append(
                f"{self._format_number(count, 'партньорски', 'партньорски', 'партньорски')} проекти"
            )

        if participation_parts:
            parts.append(f"Участие в проекти и събития: {', '.join(participation_parts)}")

        # Special programs
        special_parts = []
        if card_data.get("participation_in_live_human_treasures_national") is not None:
            count = int(card_data["participation_in_live_human_treasures_national"])
            special_parts.append(
                f"{self._format_number(count, 'национално', 'национални', 'национални')} участие в програма 'Живи човешки съкровища'"
            )
        if card_data.get("participation_in_live_human_treasures_regional") is not None:
            count = int(card_data["participation_in_live_human_treasures_regional"])
            special_parts.append(
                f"{self._format_number(count, 'регионално', 'регионални', 'регионални')} участие в програма 'Живи човешки съкровища'"
            )
        if card_data.get("disabilities_and_volunteers") is not None:
            count = int(card_data["disabilities_and_volunteers"])
            special_parts.append(
                f"{self._format_number(count, 'дейност', 'дейности', 'дейности')} за хора с увреждания и доброволци"
            )

        if special_parts:
            parts.append(f"Специални програми: {', '.join(special_parts)}")

        # Administrative positions
        if card_data.get("administrative_positions") is not None:
            count = int(card_data["administrative_positions"])
            parts.append(
                f"Административни длъжности: {self._format_number(count, 'длъжност', 'длъжности', 'длъжности')}"
            )

        # Other activities
        if card_data.get("other_activities") is not None:
            count = int(card_data["other_activities"])
            parts.append(
                f"Други дейности: {self._format_number(count, 'дейност', 'дейности', 'дейности')}"
            )

        # Technology
        if card_data.get("has_pc_and_internet_services"):
            parts.append("Има компютри и интернет услуги")

        # Town population context
        if card_data.get("town_population") is not None:
            pop = int(card_data["town_population"])
            parts.append(f"Население на града: {self._format_number(pop, 'жител', 'жители', 'жители')}")

        if card_data.get("town_users") is not None:
            users = int(card_data["town_users"])
            parts.append(
                f"Потребители от града: {self._format_number(users, 'потребител', 'потребители', 'потребители')}"
            )

        # Text fields
        if card_data.get("kraeznanie_clubs_text"):
            parts.append(f"Краезначески клубове: {card_data['kraeznanie_clubs_text']}")

        if card_data.get("language_courses_text"):
            parts.append(f"Езикови курсове: {card_data['language_courses_text']}")

        if card_data.get("museum_collections_text"):
            parts.append(f"Музейни колекции: {card_data['museum_collections_text']}")

        if card_data.get("workshops_clubs_arts_text"):
            parts.append(f"Ателиета по изкуства: {card_data['workshops_clubs_arts_text']}")

        return ". ".join(parts) + "."

    def transform_chitalishte_with_cards_to_text(
        self, chitalishte_data: dict, include_cards: bool = True
    ) -> str:
        """
        Transform Chitalishte with InformationCards to Bulgarian narrative text.

        Args:
            chitalishte_data: Dictionary containing Chitalishte data with information_cards
            include_cards: Whether to include InformationCard details

        Returns:
            Bulgarian narrative text describing the Chitalishte and its cards
        """
        parts = []

        # Chitalishte basic info
        chitalishte_text = self.transform_chitalishte_to_text(chitalishte_data)
        parts.append(chitalishte_text)

        # Information cards
        if include_cards and chitalishte_data.get("information_cards"):
            cards = chitalishte_data["information_cards"]
            chitalishte_name = chitalishte_data.get("name", "")

            parts.append("\n\nДанни за дейността:")

            for card in cards:
                card_text = self.transform_information_card_to_text(card, chitalishte_name)
                parts.append(card_text)

        return "\n\n".join(parts)

    def _format_number(self, count: int, singular: str, plural_2_4: str, plural_5plus: str) -> str:
        """
        Format number with correct Bulgarian plural form.

        Args:
            count: The number
            singular: Singular form (1)
            plural_2_4: Plural form for 2-4
            plural_5plus: Plural form for 5+

        Returns:
            Formatted string with number and correct plural form
        """
        if count == 1:
            return f"{count} {singular}"
        elif 2 <= count <= 4:
            return f"{count} {plural_2_4}"
        else:
            return f"{count} {plural_5plus}"

    def _format_decimal(self, value: float) -> str:
        """
        Format decimal number for Bulgarian text.

        Args:
            value: Decimal value

        Returns:
            Formatted string (e.g., "5.5" or "5")
        """
        if value == int(value):
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def normalize_text(self, text: str) -> str:
        """
        Normalize text encoding and clean up.

        Args:
            text: Input text

        Returns:
            Normalized text with UTF-8 encoding
        """
        # Ensure UTF-8 encoding
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        else:
            # Ensure it's a string
            text = str(text)

        # Normalize whitespace
        text = " ".join(text.split())

        # Remove excessive punctuation
        text = text.replace("..", ".")
        text = text.replace(",,", ",")

        return text.strip()

