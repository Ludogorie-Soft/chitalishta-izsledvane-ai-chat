"""Semantic transformation service - converts DB data to Bulgarian narrative text."""

from typing import Optional


class SemanticTransformationService:
    """Service for transforming raw database data into Bulgarian narrative text."""

    def __init__(self):
        """Initialize the semantic transformation service."""
        pass

    def transform_chitalishta_to_text(self, chitalishta_data: dict) -> str:
        """
        Transform Chitalishta data dictionary to Bulgarian narrative text.

        Args:
            chitalishta_data: Dictionary containing Chitalishta data

        Returns:
            Bulgarian narrative text describing the Chitalishta
        """
        parts = []

        # Basic information
        if chitalishta_data.get("name"):
            parts.append(f"Читалище: {chitalishta_data['name']}")

        if chitalishta_data.get("reg_n"):
            parts.append(f"Регистрационен номер: {chitalishta_data['reg_n']}")

        # Location information
        location_parts = []
        if chitalishta_data.get("town"):
            location_parts.append(f"град {chitalishta_data['town']}")
        if chitalishta_data.get("village_city"):
            location_parts.append(f"тип: {chitalishta_data['village_city']}")
        if chitalishta_data.get("address"):
            location_parts.append(f"адрес: {chitalishta_data['address']}")
        if chitalishta_data.get("settlement_norm"):
            location_parts.append(f"населено място: {chitalishta_data['settlement_norm']}")

        if location_parts:
            parts.append(f"Локация: {', '.join(location_parts)}")

        # Status
        # Note: status is in year_data, not in chitalishta table

        # Contact information
        contact_parts = []
        if chitalishta_data.get("phone"):
            contact_parts.append(f"телефон: {chitalishta_data['phone']}")

        if contact_parts:
            parts.append(f"Контакти: {', '.join(contact_parts)}")

        # Additional information
        if chitalishta_data.get("is_munip_center"):
            parts.append(f"Общински център: {chitalishta_data['is_munip_center']}")

        if chitalishta_data.get("empl_category"):
            parts.append(f"Категория на служителите: {chitalishta_data['empl_category']}")

        return ". ".join(parts) + "."

    def transform_chitalishte_year_data_to_text(
        self, year_data: dict, chitalishta_name: Optional[str] = None
    ) -> str:
        """
        Transform ChitalishteYearData dictionary to Bulgarian narrative text.

        Args:
            year_data: Dictionary containing ChitalishteYearData
            chitalishta_name: Optional name of the Chitalishta for context

        Returns:
            Bulgarian narrative text describing the ChitalishteYearData
        """
        parts = []

        # Year context
        year = year_data.get("year")
        if year:
            parts.append(f"Данни за {year} година")
        if chitalishta_name:
            parts.append(f"за читалище {chitalishta_name}")

        # Membership information
        membership_parts = []
        if year_data.get("total_members") is not None:
            count = int(year_data["total_members"])
            membership_parts.append(f"общо {self._format_number(count, 'член', 'члена', 'члена')}")
        if year_data.get("new_members") is not None:
            count = int(year_data["new_members"])
            membership_parts.append(
                f"{self._format_number(count, 'нов', 'нови', 'нови')} {self._format_number(count, 'член', 'члена', 'члена')}"
            )
        if year_data.get("membership_applications") is not None:
            count = int(year_data["membership_applications"])
            membership_parts.append(
                f"{self._format_number(count, 'кандидатура', 'кандидатури', 'кандидатури')} за членство"
            )
        if year_data.get("rejected_applications") is not None:
            count = int(year_data["rejected_applications"])
            membership_parts.append(
                f"{self._format_number(count, 'отказана', 'отказани', 'отказани')} {self._format_number(count, 'кандидатура', 'кандидатури', 'кандидатури')}"
            )

        if membership_parts:
            parts.append(f"Членство: {', '.join(membership_parts)}")

        # Employees/Staff
        employee_parts = []
        if year_data.get("staff_count") is not None:
            count = int(year_data["staff_count"])
            employee_parts.append(
                f"{self._format_number(count, 'служител', 'служители', 'служители')}"
            )
        if year_data.get("average_annual_staff") is not None:
            count = float(year_data["average_annual_staff"])
            employee_parts.append(f"средногодишен брой: {self._format_decimal(count)}")
        if year_data.get("staff_higher_edu") is not None:
            count = int(year_data["staff_higher_edu"])
            employee_parts.append(
                f"{self._format_number(count, 'с', 'с', 'с')} висше образование: {count}"
            )
        if year_data.get("specialized_positions") is not None:
            count = int(year_data["specialized_positions"])
            employee_parts.append(
                f"{self._format_number(count, 'специализирана', 'специализирани', 'специализирани')} длъжност: {count}"
            )
        if year_data.get("support_staff") is not None:
            count = int(year_data["support_staff"])
            employee_parts.append(
                f"{self._format_number(count, 'поддържащ', 'поддържащи', 'поддържащи')} персонал: {count}"
            )
        if year_data.get("subsidized_staff_count") is not None:
            count = int(year_data["subsidized_staff_count"])
            employee_parts.append(
                f"{self._format_number(count, 'субсидиран', 'субсидирани', 'субсидирани')} персонал: {count}"
            )

        if employee_parts:
            parts.append(f"Персонал: {', '.join(employee_parts)}")

        # Cultural activities
        activity_parts = []
        if year_data.get("folklore_groups") is not None:
            count = int(year_data["folklore_groups"])
            activity_parts.append(
                f"{self._format_number(count, 'фолклорна', 'фолклорни', 'фолклорни')} група"
            )
        if year_data.get("theater_groups") is not None:
            count = int(year_data["theater_groups"])
            activity_parts.append(
                f"{self._format_number(count, 'театрална', 'театрални', 'театрални')} група"
            )
        if year_data.get("vocal_groups") is not None:
            count = int(year_data["vocal_groups"])
            activity_parts.append(
                f"{self._format_number(count, 'вокална', 'вокални', 'вокални')} група"
            )
        if year_data.get("dance_groups") is not None:
            count = int(year_data["dance_groups"])
            activity_parts.append(
                f"{self._format_number(count, 'танцова', 'танцови', 'танцови')} група"
            )
        if year_data.get("classical_dance_groups") is not None:
            count = int(year_data["classical_dance_groups"])
            activity_parts.append(
                f"{self._format_number(count, 'класическа', 'класически', 'класически')} танцова група"
            )
        if year_data.get("art_clubs") is not None:
            count = int(year_data["art_clubs"])
            activity_parts.append(
                f"{self._format_number(count, 'художествен', 'художествени', 'художествени')} клуб"
            )

        if activity_parts:
            parts.append(f"Културни формации: {', '.join(activity_parts)}")

        # Clubs and activities
        club_parts = []
        if year_data.get("local_history_clubs") is not None:
            count = int(year_data["local_history_clubs"])
            club_parts.append(
                f"{self._format_number(count, 'краезначески', 'краезначески', 'краезначески')} клуб"
            )
        if year_data.get("language_schools") is not None:
            count = int(year_data["language_schools"])
            club_parts.append(
                f"{self._format_number(count, 'езикова', 'езикови', 'езикови')} школа"
            )
        if year_data.get("other_clubs") is not None:
            count = int(year_data["other_clubs"])
            club_parts.append(f"{self._format_number(count, 'друг', 'други', 'други')} клуб")

        if club_parts:
            parts.append(f"Клубове и курсове: {', '.join(club_parts)}")

        # Library activity (now TEXT field, not INTEGER)
        if year_data.get("library_activity"):
            parts.append(f"Библиотечна дейност: {year_data['library_activity']}")

        # Library statistics
        library_parts = []
        if year_data.get("library_units") is not None:
            count = int(year_data["library_units"])
            library_parts.append(
                f"{self._format_number(count, 'библиотечна', 'библиотечни', 'библиотечни')} единица"
            )
        if year_data.get("library_users") is not None:
            count = int(year_data["library_users"])
            library_parts.append(
                f"{self._format_number(count, 'потребител', 'потребители', 'потребители')}"
            )
        if year_data.get("library_users_online") is not None:
            count = int(year_data["library_users_online"])
            library_parts.append(f"онлайн потребители: {count}")
        if year_data.get("borrowed_documents") is not None:
            count = int(year_data["borrowed_documents"])
            library_parts.append(f"{self._format_number(count, 'зает', 'заети', 'заети')} документ")

        if library_parts:
            parts.append(f"Библиотека: {', '.join(library_parts)}")

        # Museum collections
        if year_data.get("museum_collections") is not None:
            count = int(year_data["museum_collections"])
            parts.append(
                f"Музейни колекции: {self._format_number(count, 'колекция', 'колекции', 'колекции')}"
            )

        # Participation
        participation_parts = []
        if year_data.get("event_participations") is not None:
            count = int(year_data["event_participations"])
            participation_parts.append(
                f"{self._format_number(count, 'участие', 'участия', 'участия')} в събития"
            )
        if year_data.get("training_participation") is not None:
            count = int(year_data["training_participation"])
            participation_parts.append(
                f"{self._format_number(count, 'участие', 'участия', 'участия')} в обучения"
            )
        if year_data.get("independent_projects") is not None:
            count = int(year_data["independent_projects"])
            participation_parts.append(
                f"{self._format_number(count, 'независим', 'независими', 'независими')} проект"
            )
        if year_data.get("collaborative_projects") is not None:
            count = int(year_data["collaborative_projects"])
            participation_parts.append(
                f"{self._format_number(count, 'партньорски', 'партньорски', 'партньорски')} проект"
            )
        if year_data.get("national_projects") is not None:
            count = int(year_data["national_projects"])
            participation_parts.append(
                f"{self._format_number(count, 'национален', 'национални', 'национални')} проект"
            )
        if year_data.get("regional_projects") is not None:
            count = int(year_data["regional_projects"])
            participation_parts.append(
                f"{self._format_number(count, 'регионален', 'регионални', 'регионални')} проект"
            )
        if year_data.get("international_projects") is not None:
            count = int(year_data["international_projects"])
            participation_parts.append(
                f"{self._format_number(count, 'международен', 'международни', 'международни')} проект"
            )

        if participation_parts:
            parts.append(f"Участие в проекти и събития: {', '.join(participation_parts)}")

        # Administrative positions
        if year_data.get("administrative_positions") is not None:
            count = int(year_data["administrative_positions"])
            parts.append(
                f"Административни длъжности: {self._format_number(count, 'длъжност', 'длъжности', 'длъжности')}"
            )

        # Other activities (now TEXT field)
        if year_data.get("other_activities"):
            parts.append(f"Други дейности: {year_data['other_activities']}")

        # Technology
        if year_data.get("internet_access") is not None:
            count = int(year_data["internet_access"])
            if count > 0:
                parts.append("Има интернет достъп")
        if year_data.get("computerized_workstations") is not None:
            count = int(year_data["computerized_workstations"])
            if count > 0:
                parts.append(
                    f"Компютризирани работни места: {self._format_number(count, 'място', 'места', 'места')}"
                )

        # Text fields
        if year_data.get("local_history_clubs_text"):
            parts.append(f"Краезначески клубове: {year_data['local_history_clubs_text']}")

        if year_data.get("language_schools_text"):
            parts.append(f"Езикови школи: {year_data['language_schools_text']}")

        if year_data.get("museum_collections_text"):
            parts.append(f"Музейни колекции: {year_data['museum_collections_text']}")

        if year_data.get("art_clubs_text"):
            parts.append(f"Художествени клубове: {year_data['art_clubs_text']}")

        # Financial data (if available)
        financial_parts = []
        if year_data.get("total_income") is not None:
            income = float(year_data["total_income"])
            financial_parts.append(f"общ доход: {self._format_decimal(income)} лв")
        if year_data.get("total_expenditure") is not None:
            expenditure = float(year_data["total_expenditure"])
            financial_parts.append(f"общ разход: {self._format_decimal(expenditure)} лв")
        if year_data.get("profit") is not None:
            profit = float(year_data["profit"])
            financial_parts.append(f"печалба: {self._format_decimal(profit)} лв")
        elif year_data.get("loss") is not None:
            loss = float(year_data["loss"])
            financial_parts.append(f"загуба: {self._format_decimal(loss)} лв")

        if financial_parts:
            parts.append(f"Финанси: {', '.join(financial_parts)}")

        return ". ".join(parts) + "."

    def transform_chitalishta_with_year_data_to_text(
        self, chitalishta_data: dict, include_year_data: bool = True
    ) -> str:
        """
        Transform Chitalishta with ChitalishteYearData to Bulgarian narrative text.

        Args:
            chitalishta_data: Dictionary containing Chitalishta data with chitalishte_year_data
            include_year_data: Whether to include ChitalishteYearData details

        Returns:
            Bulgarian narrative text describing the Chitalishta and its year data
        """
        parts = []

        # Chitalishta basic info
        chitalishta_text = self.transform_chitalishta_to_text(chitalishta_data)
        parts.append(chitalishta_text)

        # Year data
        if include_year_data and chitalishta_data.get("chitalishte_year_data"):
            year_data_list = chitalishta_data["chitalishte_year_data"]
            chitalishta_name = chitalishta_data.get("name", "")

            parts.append("\n\nДанни за дейността:")

            for year_data in year_data_list:
                year_data_text = self.transform_chitalishte_year_data_to_text(
                    year_data, chitalishta_name
                )
                parts.append(year_data_text)

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
