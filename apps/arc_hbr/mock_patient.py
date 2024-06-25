from typing import Any
from faker import Faker
from dataclasses import dataclass, field
import numpy as np

@dataclass
class Random:
    seed: int
    missingness: float = 0.2
    rng: np.random.Generator = field(init=False)
    faker: Faker = field(init=False)

    def __post_init__(self):
        self.rng = np.random.default_rng(seed=self.seed)
        self.faker = Faker(seed=self.seed)
        
    def random_name(self):
        return self.faker.name()

    def random_tnumber(self):
        num = int(self.rng.uniform(0, 9999999))
        return f"T{num:>07}"
        
    def random_choice(self, choices: list[Any]) -> Any | None:
        other_weight = (1 - self.missingness) / len(choices)
        weights = [self.missingness] + [other_weight] * len(choices)

        return self.rng.choice([None] + choices, p = weights)
    
    def random_int(self, center: int, scale: int) -> int | None:
        val = int(self.rng.normal(center, scale))
        return self.random_choice([val])

    def random_float(self, center: float, scale: float, dp: int) -> float | None:
        """Random real number rounded to decimal places
        """
        val = round(self.rng.normal(center, scale), dp)
        return self.random_choice([val])
    
    def random_patient(self) -> dict[str, str | int | float | None]:
        """Create mock patient data
        
        This simulates data that might be fetched from backend
        data sources automatically.
        """
        return {
            "name": self.random_name(),
            "t_number": self.random_tnumber(),
            "age": self.random_int(70, 10),
            "oac": self.random_choice(["Yes", "No"]),
            "gender": self.random_choice(["Male", "Female"]),
            "hb": self.random_float(12, 2, 1),
            "platelets": self.random_int(150, 100),
            "egfr": self.random_int(60, 50),
            "prior_bleeding": self.random_choice([
                "< 6 months or recurrent",
                "< 12 months",
                "No bleeding"
            ]),
            "cirrhosis_ptl_hyp": self.random_choice(["Yes", "No"]),
            "nsaid": self.random_choice(["Yes", "No"]),
            "cancer": self.random_choice(["Yes", "No"]),
            "prior_ich_stroke": self.random_choice([
                "bAVM, ICH, or moderate/severe ischaemic stroke < 6 months",
                "Any prior ischaemic stroke",
                "No ICH/ischaemic stroke"
            ]),
            "prior_surgery_trauma": self.random_choice(["Yes", "No"]),
            "planned_surgery": self.random_choice(["Yes", "No"]),
        }


    


