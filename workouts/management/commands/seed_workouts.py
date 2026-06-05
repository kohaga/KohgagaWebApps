from django.core.management.base import BaseCommand

from workouts.models import (
    Equipment,
    Exercise,
    ExerciseMuscle,
    MuscleGroup,
)


class Command(BaseCommand):
    help = "Seed initial workout master data in Hungarian."

    def handle(self, *args, **options):
        self.seed_muscle_groups()
        self.seed_equipment()
        self.seed_exercises()

        self.stdout.write(
            self.style.SUCCESS("Workout seed data loaded successfully.")
        )

    def get_or_create_by_aliases(self, model, name, aliases, defaults):
        lookup_names = [name] + aliases
        instance = model.objects.filter(name__in=lookup_names).first()

        if instance:
            for field, value in defaults.items():
                setattr(instance, field, value)
            instance.name = name
            instance.save()
            return instance

        return model.objects.create(name=name, **defaults)

    def seed_muscle_groups(self):
        muscle_groups = [
            {
                "name": "Mell",
                "aliases": ["Chest"],
                "description": "Mellizmok, főként a nagy és kis mellizom.",
            },
            {
                "name": "Hát",
                "aliases": ["Back"],
                "description": "Felső és középső hátizmok.",
            },
            {
                "name": "Széles hátizom",
                "aliases": ["Lats"],
                "description": "Széles hátizom, főként húzó mozgásoknál dolgozik.",
            },
            {
                "name": "Váll",
                "aliases": ["Shoulders"],
                "description": "Deltaizmok.",
            },
            {
                "name": "Bicepsz",
                "aliases": ["Biceps"],
                "description": "Felkar elülső izmai.",
            },
            {
                "name": "Tricepsz",
                "aliases": ["Triceps"],
                "description": "Felkar hátsó izmai.",
            },
            {
                "name": "Comb elülső része",
                "aliases": ["Quadriceps"],
                "description": "Négyfejű combizom, főként guggoló mozgásoknál dolgozik.",
            },
            {
                "name": "Comb hátsó része",
                "aliases": ["Hamstrings"],
                "description": "Hátsó combizmok.",
            },
            {
                "name": "Farizom",
                "aliases": ["Glutes"],
                "description": "Farizmok.",
            },
            {
                "name": "Törzs",
                "aliases": ["Core"],
                "description": "Hasizmok és törzsstabilizáló izmok.",
            },
            {
                "name": "Vádli",
                "aliases": ["Calves"],
                "description": "Alsó lábszár izmai.",
            },
            {
                "name": "Kardió",
                "aliases": ["Cardio"],
                "description": "Állóképességi, keringésfejlesztő munka.",
            },
        ]

        for item in muscle_groups:
            self.get_or_create_by_aliases(
                MuscleGroup,
                name=item["name"],
                aliases=item["aliases"],
                defaults={"description": item["description"]},
            )

    def seed_equipment(self):
        equipment_items = [
            {
                "name": "Saját testsúly",
                "aliases": ["Bodyweight"],
                "description": "Nincs szükség külső eszközre.",
            },
            {
                "name": "Futópad",
                "aliases": ["Treadmill"],
                "description": "Sétához vagy futáshoz használható gép.",
            },
            {
                "name": "Állítható kézisúlyzó",
                "aliases": ["Adjustable dumbbells"],
                "description": "Állítható súlyú kézisúlyzó pár.",
            },
            {
                "name": "Edzőpad",
                "aliases": ["Bench"],
                "description": "Fekvő, nyomó és támaszos gyakorlatokhoz használható pad.",
            },
            {
                "name": "Kettlebell",
                "aliases": ["Kettlebell"],
                "description": "Guggolásokhoz, lendítésekhez és cipelésekhez használható eszköz.",
            },
            {
                "name": "Húzódzkodó / tolódzkodó állvány",
                "aliases": ["Pull-up / dip station"],
                "description": "Húzódzkodáshoz, tolódzkodáshoz és függeszkedéshez használható állvány.",
            },
            {
                "name": "Csigás gép",
                "aliases": ["Cable machine"],
                "description": "Lehúzásokhoz és csigás gyakorlatokhoz használható gép.",
            },
            {
                "name": "Jógamatrac",
                "aliases": ["Yoga mat"],
                "description": "Talajgyakorlatokhoz és mobilitási munkához használható matrac.",
            },
        ]

        for item in equipment_items:
            self.get_or_create_by_aliases(
                Equipment,
                name=item["name"],
                aliases=item["aliases"],
                defaults={"description": item["description"]},
            )

    def seed_exercises(self):
        exercises = [
            {
                "name": "Tempós séta futópadon",
                "aliases": ["Treadmill brisk walk"],
                "description": (
                    "Sétálj a futópadon kényelmes, de aktív tempóban. "
                    "Tartsd a törzsed egyenesen, a vállad legyen laza, a karod mozogjon természetesen."
                ),
                "coaching_cues": (
                    "Lehetőleg ne kapaszkodj a fogantyúba, csak ha biztonság miatt szükséges. "
                    "A tempó legyen beszélgetős, de érezhetően aktív."
                ),
                "movement_pattern": Exercise.MovementPattern.CARDIO,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 1,
                "default_reps_min": 1,
                "default_reps_max": 1,
                "default_rest_seconds": 30,
                "is_bodyweight": True,
                "is_unilateral": False,
                "equipment": ["Futópad"],
                "muscles": [
                    ("Kardió", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Vádli", ExerciseMuscle.MuscleRole.SECONDARY),
                    ("Farizom", ExerciseMuscle.MuscleRole.SECONDARY),
                ],
            },
            {
                "name": "Goblet guggolás",
                "aliases": ["Goblet squat"],
                "description": (
                    "Tarts egy kézisúlyzót vagy kettlebellt a mellkasod előtt. "
                    "Guggolj le kontrolláltan térd- és csípőhajlítással, majd állj vissza. "
                    "A mellkas maradjon kiemelve, a térdek kövessék a lábfej irányát."
                ),
                "coaching_cues": (
                    "Ne engedd befelé esni a térdeket. "
                    "A súly maradjon közel a testhez. "
                    "Csak addig menj le, amíg kontrolláltan tudod tartani a mozgást."
                ),
                "movement_pattern": Exercise.MovementPattern.SQUAT,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 8,
                "default_reps_max": 12,
                "default_rest_seconds": 90,
                "is_bodyweight": False,
                "is_unilateral": False,
                "equipment": ["Állítható kézisúlyzó", "Kettlebell"],
                "muscles": [
                    ("Comb elülső része", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Farizom", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Törzs", ExerciseMuscle.MuscleRole.SECONDARY),
                ],
            },
            {
                "name": "Kézisúlyzós fekvenyomás",
                "aliases": ["Dumbbell bench press"],
                "description": (
                    "Feküdj az edzőpadra, mindkét kezedben egy-egy kézisúlyzóval. "
                    "Nyomd fel a súlyokat, amíg a karod majdnem teljesen nyújtott, "
                    "majd kontrolláltan engedd vissza mellkas szintig."
                ),
                "coaching_cues": (
                    "A lapockák maradjanak stabilan a padon. "
                    "Ne pattintsd meg a súlyt. "
                    "A leengedés legyen lassú és kontrollált."
                ),
                "movement_pattern": Exercise.MovementPattern.PUSH,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 8,
                "default_reps_max": 12,
                "default_rest_seconds": 90,
                "is_bodyweight": False,
                "is_unilateral": False,
                "equipment": ["Állítható kézisúlyzó", "Edzőpad"],
                "muscles": [
                    ("Mell", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Tricepsz", ExerciseMuscle.MuscleRole.SECONDARY),
                    ("Váll", ExerciseMuscle.MuscleRole.SECONDARY),
                ],
            },
            {
                "name": "Egykezes kézisúlyzós evezés",
                "aliases": ["One-arm dumbbell row"],
                "description": (
                    "Támaszkodj az edzőpadra egyik kézzel és egyik térddel. "
                    "Húzd a kézisúlyzót a csípőd irányába, majd kontrolláltan engedd vissza."
                ),
                "coaching_cues": (
                    "Ne csavard el a törzsed. "
                    "Könyökkel húzz, ne kézből. "
                    "A hát maradjon semleges helyzetben."
                ),
                "movement_pattern": Exercise.MovementPattern.PULL,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 8,
                "default_reps_max": 12,
                "default_rest_seconds": 75,
                "is_bodyweight": False,
                "is_unilateral": True,
                "equipment": ["Állítható kézisúlyzó", "Edzőpad"],
                "muscles": [
                    ("Hát", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Széles hátizom", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Bicepsz", ExerciseMuscle.MuscleRole.SECONDARY),
                    ("Törzs", ExerciseMuscle.MuscleRole.STABILIZER),
                ],
            },
            {
                "name": "Mellhez húzás csigán",
                "aliases": ["Lat pulldown to chest"],
                "description": (
                    "Ülj be a csigás géphez, és húzd le a rudat a mellkas felső részéhez. "
                    "Ezután kontrolláltan engedd vissza, amíg a karod újra kinyúlik."
                ),
                "coaching_cues": (
                    "Mellhez húzd, ne tarkó mögé. "
                    "A mellkas maradjon kiemelve. "
                    "Ne dőlj túlzottan hátra."
                ),
                "movement_pattern": Exercise.MovementPattern.PULL,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 8,
                "default_reps_max": 12,
                "default_rest_seconds": 90,
                "is_bodyweight": False,
                "is_unilateral": False,
                "equipment": ["Csigás gép"],
                "muscles": [
                    ("Széles hátizom", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Hát", ExerciseMuscle.MuscleRole.SECONDARY),
                    ("Bicepsz", ExerciseMuscle.MuscleRole.SECONDARY),
                ],
            },
            {
                "name": "Kézisúlyzós román felhúzás",
                "aliases": ["Dumbbell Romanian deadlift"],
                "description": (
                    "Tarts kézisúlyzókat a combod előtt. "
                    "Toldd hátra a csípőd semleges háttal, majd a csípő előretolásával állj vissza."
                ),
                "coaching_cues": (
                    "Ez csípőhajlítás, nem guggolás. "
                    "A súlyok maradjanak közel a lábadhoz. "
                    "Állj meg, mielőtt a derekad elkezdene gömbölyödni."
                ),
                "movement_pattern": Exercise.MovementPattern.HINGE,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 8,
                "default_reps_max": 12,
                "default_rest_seconds": 90,
                "is_bodyweight": False,
                "is_unilateral": False,
                "equipment": ["Állítható kézisúlyzó"],
                "muscles": [
                    ("Comb hátsó része", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Farizom", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Törzs", ExerciseMuscle.MuscleRole.STABILIZER),
                ],
            },
            {
                "name": "Kézisúlyzós bicepszhajlítás",
                "aliases": ["Dumbbell biceps curl"],
                "description": (
                    "Állj egyenesen, mindkét kézben kézisúlyzóval. "
                    "Hajlítsd a könyököd, emeld fel a súlyokat, majd lassan engedd vissza."
                ),
                "coaching_cues": (
                    "A könyök maradjon közel a törzshöz. "
                    "Ne lendítsd a felsőtested. "
                    "A leengedés legyen kontrollált."
                ),
                "movement_pattern": Exercise.MovementPattern.ARMS,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 10,
                "default_reps_max": 15,
                "default_rest_seconds": 60,
                "is_bodyweight": False,
                "is_unilateral": False,
                "equipment": ["Állítható kézisúlyzó"],
                "muscles": [
                    ("Bicepsz", ExerciseMuscle.MuscleRole.PRIMARY),
                ],
            },
            {
                "name": "Fej fölötti kézisúlyzós tricepsznyújtás",
                "aliases": ["Overhead dumbbell triceps extension"],
                "description": (
                    "Tarts egy kézisúlyzót két kézzel a fejed fölött. "
                    "Hajlítsd a könyököd, engedd a súlyt a fejed mögé, majd nyújtsd vissza a karod."
                ),
                "coaching_cues": (
                    "A könyök lehetőleg előre nézzen, ne nyíljon szét nagyon oldalra. "
                    "Ne homoríts túl a derekaddal. "
                    "Kontrollált mozgástartományban dolgozz."
                ),
                "movement_pattern": Exercise.MovementPattern.ARMS,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 10,
                "default_reps_max": 15,
                "default_rest_seconds": 60,
                "is_bodyweight": False,
                "is_unilateral": False,
                "equipment": ["Állítható kézisúlyzó"],
                "muscles": [
                    ("Tricepsz", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Törzs", ExerciseMuscle.MuscleRole.STABILIZER),
                ],
            },
            {
                "name": "Plank",
                "aliases": ["Plank"],
                "description": (
                    "Tartsd a tested egyenes vonalban alkartámaszban és lábujjtámaszban. "
                    "A fej, törzs és sarok lehetőleg egy vonalban legyen."
                ),
                "coaching_cues": (
                    "Ne essen be a csípőd. "
                    "Ne told túl magasra a feneked. "
                    "Feszítsd a törzsed, és közben lélegezz folyamatosan."
                ),
                "movement_pattern": Exercise.MovementPattern.CORE,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 30,
                "default_reps_max": 45,
                "default_rest_seconds": 45,
                "is_bodyweight": True,
                "is_unilateral": False,
                "equipment": ["Jógamatrac"],
                "muscles": [
                    ("Törzs", ExerciseMuscle.MuscleRole.PRIMARY),
                    ("Váll", ExerciseMuscle.MuscleRole.SECONDARY),
                ],
            },
            {
                "name": "Hasprés",
                "aliases": ["Crunch"],
                "description": (
                    "Feküdj hanyatt behajlított térddel. "
                    "A hasizmod megfeszítésével emeld el a felső hátad a talajtól, "
                    "majd lassan engedd vissza."
                ),
                "coaching_cues": (
                    "Ne húzd a nyakad. "
                    "A mozgás legyen kicsi és kontrollált. "
                    "A hasizom összehúzódására figyelj."
                ),
                "movement_pattern": Exercise.MovementPattern.CORE,
                "difficulty": Exercise.Difficulty.BEGINNER,
                "default_sets": 3,
                "default_reps_min": 12,
                "default_reps_max": 20,
                "default_rest_seconds": 45,
                "is_bodyweight": True,
                "is_unilateral": False,
                "equipment": ["Jógamatrac"],
                "muscles": [
                    ("Törzs", ExerciseMuscle.MuscleRole.PRIMARY),
                ],
            },
        ]

        for item in exercises:
            exercise = self.get_or_create_by_aliases(
                Exercise,
                name=item["name"],
                aliases=item["aliases"],
                defaults={
                    "description": item["description"],
                    "coaching_cues": item["coaching_cues"],
                    "movement_pattern": item["movement_pattern"],
                    "difficulty": item["difficulty"],
                    "default_sets": item["default_sets"],
                    "default_reps_min": item["default_reps_min"],
                    "default_reps_max": item["default_reps_max"],
                    "default_rest_seconds": item["default_rest_seconds"],
                    "is_bodyweight": item["is_bodyweight"],
                    "is_unilateral": item["is_unilateral"],
                    "is_active": True,
                },
            )

            exercise.equipment.clear()
            for equipment_name in item["equipment"]:
                equipment = Equipment.objects.get(name=equipment_name)
                exercise.equipment.add(equipment)

            ExerciseMuscle.objects.filter(exercise=exercise).delete()
            for muscle_name, role in item["muscles"]:
                muscle_group = MuscleGroup.objects.get(name=muscle_name)
                ExerciseMuscle.objects.create(
                    exercise=exercise,
                    muscle_group=muscle_group,
                    role=role,
                )