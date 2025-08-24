import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import asyncio
import csv
from typing import Optional, Dict
from .presidential_winners import PRESIDENTIAL_STATE_DATA

# Demographic voting bloc thresholds
DEMOGRAPHIC_THRESHOLDS = {
    "Urban Voters": 25,
    "Suburban Voters": 20,
    "Rural Voters": 18,
    "Evangelical Christians": 18,
    "African American Voters": 22,
    "Latino/Hispanic Voters": 22,
    "Asian American Voters": 18,
    "Blue-Collar / Working-Class Voters": 20,
    "College-Educated Professionals": 20,
    "Young Voters (18–29)": 20,
    "Senior Citizens (65+)": 18,
    "Native American Voters": 12,
    "Military & Veteran Voters": 15,
    "LGBTQ+ Voters": 15,
    "Immigrant Communities": 15,
    "Tech & Innovation Workers": 18,
    "Wealthy / High-Income Voters": 15,
    "Low-Income Voters": 22,
    "Environmental & Green Voters": 18,
    "Gun Rights Advocates": 18
}

# Backlash system - opposing voter blocs
DEMOGRAPHIC_CONFLICTS = {
    "Urban Voters": ["Rural Voters", "Gun Rights Advocates"],
    "Suburban Voters": ["Rural Voters"],
    "Rural Voters": ["Urban Voters", "Suburban Voters", "Environmental & Green Voters"],
    "Evangelical Christians": ["LGBTQ+ Voters", "Immigrant Communities", "Young Voters (18–29)"],
    "African American Voters": ["Gun Rights Advocates"],
    "Latino/Hispanic Voters": ["Gun Rights Advocates"],
    "Asian American Voters": ["Gun Rights Advocates"],
    "Blue-Collar / Working-Class Voters": ["College-Educated Professionals", "Tech & Innovation Workers", "Wealthy / High-Income Voters"],
    "College-Educated Professionals": ["Blue-Collar / Working-Class Voters", "Gun Rights Advocates"],
    "Young Voters (18–29)": ["Senior Citizens (65+)", "Evangelical Christians"],
    "Senior Citizens (65+)": ["Young Voters (18–29)", "Tech & Innovation Workers"],
    "Native American Voters": ["Gun Rights Advocates"],
    "Military & Veteran Voters": ["Environmental & Green Voters", "LGBTQ+ Voters"],
    "LGBTQ+ Voters": ["Evangelical Christians", "Military & Veteran Voters"],
    "Immigrant Communities": ["Evangelical Christians", "Gun Rights Advocates"],
    "Tech & Innovation Workers": ["Blue-Collar / Working-Class Voters", "Senior Citizens (65+)", "Gun Rights Advocates"],
    "Wealthy / High-Income Voters": ["Low-Income Voters", "Blue-Collar / Working-Class Voters"],
    "Low-Income Voters": ["Wealthy / High-Income Voters"],
    "Environmental & Green Voters": ["Gun Rights Advocates", "Rural Voters", "Military & Veteran Voters"],
    "Gun Rights Advocates": ["Environmental & Green Voters", "Urban Voters", "College-Educated Professionals", "African American Voters", "Latino/Hispanic Voters", "Asian American Voters", "Native American Voters", "Immigrant Communities", "Tech & Innovation Workers"]
}

class Demographics(commands.Cog):
    def _convert_strength_to_value(self, strength):
        """Convert text strength to numeric value"""
        strength_map = {
            "Small": 0.3,
            "Moderate": 0.75,
            "Strong": 1.75
        }
        return strength_map.get(strength, 0.75)  # Default to moderate

    # State demographic strengths based on actual data
    # Small = 0.3, Moderate = 0.75, Strong = 1.75
    STATE_DEMOGRAPHICS = {
        "ALABAMA": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 1.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.3,
            "Young Voters (18–29)": 0.3, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.3, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.3, "Wealthy / High-Income Voters": 0.3, "Low-Income Voters": 1.75,
            "Environmental & Green Voters": 0.3, "Gun Rights Advocates": 1.75
        },
        "ALASKA": {
            "Urban Voters": 0.3, "Suburban Voters": 0.3, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.3, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 1.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "ARIZONA": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.3, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 1.75, "Native American Voters": 1.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "ARKANSAS": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 1.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.3,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.3, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.3, "Wealthy / High-Income Voters": 0.3, "Low-Income Voters": 1.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "CALIFORNIA": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.3,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.3, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 1.75, "Low-Income Voters": 0.3,
            "Environmental & Green Voters": 1.75, "Gun Rights Advocates": 0.3
        },
        "COLORADO": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "CONNECTICUT": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.3,
            "Evangelical Christians": 0.3, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.3,
            "Military & Veteran Voters": 0.3, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 1.75, "Low-Income Voters": 0.3,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.3
        },
        "DELAWARE": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 1.75, "Native American Voters": 0.3,
            "Military & Veteran Voters": 0.3, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "FLORIDA": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.3, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.3, "Senior Citizens (65+)": 1.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "GEORGIA": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 1.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.3, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "HAWAII": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.3,
            "Evangelical Christians": 0.3, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.3, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 1.75, "Gun Rights Advocates": 0.3
        },
        "IDAHO": {
            "Urban Voters": 0.3, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 1.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "ILLINOIS": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "INDIANA": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "IOWA": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "KANSAS": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "KENTUCKY": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 1.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.3,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.3, "Low-Income Voters": 1.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "LOUISIANA": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 1.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.3,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.3, "Low-Income Voters": 1.75,
            "Environmental & Green Voters": 0.3, "Gun Rights Advocates": 0.75
        },
        "MAINE": {
            "Urban Voters": 0.3, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.3,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.3, "Senior Citizens (65+)": 1.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.3,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 1.75, "Gun Rights Advocates": 0.75
        },
        "MARYLAND": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.3,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 1.75, "Low-Income Voters": 0.3,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.3
        },
        "MASSACHUSETTS": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.3,
            "Evangelical Christians": 0.3, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.3,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 1.75, "Low-Income Voters": 0.3,
            "Environmental & Green Voters": 1.75, "Gun Rights Advocates": 0.3
        },
        "MICHIGAN": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "MINNESOTA": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "MISSISSIPPI": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 1.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.3,
            "Young Voters (18–29)": 0.3, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.3, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.3, "Wealthy / High-Income Voters": 0.3, "Low-Income Voters": 1.75,
            "Environmental & Green Voters": 0.3, "Gun Rights Advocates": 1.75
        },
        "MISSOURI": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 1.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "MONTANA": {
            "Urban Voters": 0.3, "Suburban Voters": 0.3, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.3,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.3, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 1.75, "Native American Voters": 1.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.3,
            "Tech & Innovation Workers": 0.3, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "NEBRASKA": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "NEVADA": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.3,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.3, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "NEW HAMPSHIRE": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "NEW JERSEY": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.3,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.3,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 1.75, "Low-Income Voters": 0.3,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.3
        },
        "NEW MEXICO": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 1.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.3, "Low-Income Voters": 1.75,
            "Environmental & Green Voters": 1.75, "Gun Rights Advocates": 0.75
        },
        "NEW YORK": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 1.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.3
        },
        "NORTH CAROLINA": {
            "Urban Voters": 0.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 1.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "NORTH DAKOTA": {
            "Urban Voters": 0.3, "Suburban Voters": 0.3, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.3,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 1.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.3, "Immigrant Communities": 0.3,
            "Tech & Innovation Workers": 0.3, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.3, "Gun Rights Advocates": 1.75
        },
        "OHIO": {
            "Urban Voters": 0.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "OKLAHOMA": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 1.75,
            "Evangelical Christians": 1.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.3,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 1.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.3, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.3, "Gun Rights Advocates": 1.75
        },
        "OREGON": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.3, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 1.75, "Gun Rights Advocates": 0.75
        },
        "PENNSYLVANIA": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 1.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "RHODE ISLAND": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.3,
            "Evangelical Christians": 0.3, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.3,
            "Military & Veteran Voters": 0.3, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.3
        },
        "SOUTH CAROLINA": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 1.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 1.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "SOUTH DAKOTA": {
            "Urban Voters": 0.3, "Suburban Voters": 0.3, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.3,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 1.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.3, "Immigrant Communities": 0.3,
            "Tech & Innovation Workers": 0.3, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "TENNESSEE": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 1.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "TEXAS": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 1.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 1.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.3, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "UTAH": {
            "Urban Voters": 0.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.3, "Native American Voters": 1.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 1.75
        },
        "VERMONT": {
            "Urban Voters": 0.3, "Suburban Voters": 0.3, "Rural Voters": 1.75,
            "Evangelical Christians": 0.3, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.3,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.3, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.3,
            "Military & Veteran Voters": 0.3, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.3,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 1.75, "Gun Rights Advocates": 0.75
        },
        "VIRGINIA": {
            "Urban Voters": 1.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 1.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 1.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 1.75, "Low-Income Voters": 0.3,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "WASHINGTON": {
            "Urban Voters": 1.75, "Suburban Voters": 0.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.3, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 1.75, "Blue-Collar / Working-Class Voters": 0.75, "College-Educated Professionals": 1.75,
            "Young Voters (18–29)": 1.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 1.75, "Immigrant Communities": 1.75,
            "Tech & Innovation Workers": 1.75, "Wealthy / High-Income Voters": 1.75, "Low-Income Voters": 0.3,
            "Environmental & Green Voters": 1.75, "Gun Rights Advocates": 0.75
        },
        "WEST VIRGINIA": {
            "Urban Voters": 0.3, "Suburban Voters": 0.3, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.3,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 0.3,
            "Young Voters (18–29)": 0.3, "Senior Citizens (65+)": 1.75, "Native American Voters": 0.3,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.3, "Immigrant Communities": 0.3,
            "Tech & Innovation Workers": 0.3, "Wealthy / High-Income Voters": 0.3, "Low-Income Voters": 1.75,
            "Environmental & Green Voters": 0.3, "Gun Rights Advocates": 1.75
        },
        "WISCONSIN": {
            "Urban Voters": 0.75, "Suburban Voters": 1.75, "Rural Voters": 0.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.75, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.75, "Blue-Collar / Working-Class Voters": 1.75, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 0.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.75,
            "Tech & Innovation Workers": 0.75, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.75, "Gun Rights Advocates": 0.75
        },
        "WYOMING": {
            "Urban Voters": 0.3, "Suburban Voters": 0.3, "Rural Voters": 1.75,
            "Evangelical Christians": 0.75, "African American Voters": 0.3, "Latino/Hispanic Voters": 0.75,
            "Asian American Voters": 0.3, "Blue-Collar / Working-Class Voters": 0.3, "College-Educated Professionals": 0.75,
            "Young Voters (18–29)": 0.75, "Senior Citizens (65+)": 0.75, "Native American Voters": 1.75,
            "Military & Veteran Voters": 0.75, "LGBTQ+ Voters": 0.75, "Immigrant Communities": 0.3,
            "Tech & Innovation Workers": 0.3, "Wealthy / High-Income Voters": 0.75, "Low-Income Voters": 0.75,
            "Environmental & Green Voters": 0.3, "Gun Rights Advocates": 1.75
        }
    }

    def __init__(self, bot):
        self.bot = bot
        print("Demographics cog loaded successfully")

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_presidential_config(self, guild_id: int):
        """Get presidential signups configuration"""
        col = self.bot.db["presidential_signups"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_presidential_winners_config(self, guild_id: int):
        """Get presidential winners configuration"""
        col = self.bot.db["presidential_winners"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_user_presidential_candidate(self, guild_id: int, user_id: int):
        """Get user's presidential candidate information"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # Look in presidential winners collection for general campaign
            winners_col, winners_config = self._get_presidential_winners_config(guild_id)

            if not winners_config:
                return None, None

            # For general campaign, look for primary winners from the previous year if we're in an even year
            # Or current year if odd year
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year

            for winner in winners_config.get("winners", []):
                if (winner["user_id"] == user_id and 
                    winner.get("primary_winner", False) and 
                    winner["year"] == primary_year and
                    winner["office"] in ["President", "Vice President"]):
                    return winners_col, winner

            return winners_col, None
        else:
            return None, None

    def _get_presidential_candidate_by_name(self, guild_id: int, candidate_name: str):
        """Get presidential candidate by name"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # Look in presidential winners collection for general campaign
            winners_col, winners_config = self._get_presidential_winners_config(guild_id)

            if not winners_config:
                return None, None

            # For general campaign, look for primary winners from the previous year if we're in an even year
            # Or current year if odd year
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year

            for winner in winners_config.get("winners", []):
                if (winner["name"].lower() == candidate_name.lower() and 
                    winner.get("primary_winner", False) and
                    winner["year"] == primary_year and
                    winner["office"] in ["President", "Vice President"]):
                    return winners_col, winner

            return winners_col, None
        else:
            return None, None

    def _check_cooldown(self, guild_id: int, user_id: int, action_type: str, cooldown_hours: int):
        """Check if user is on cooldown for a specific action"""
        cooldowns_col = self.bot.db["demographic_cooldowns"]
        cooldown_record = cooldowns_col.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "action_type": action_type
        })

        if not cooldown_record:
            return True  # No cooldown record, user can proceed

        last_action = cooldown_record["last_action"]
        cooldown_end = last_action + timedelta(hours=cooldown_hours)

        return datetime.utcnow() >= cooldown_end

    def _set_cooldown(self, guild_id: int, user_id: int, action_type: str):
        """Set cooldown for a specific action"""
        cooldowns_col = self.bot.db["demographic_cooldowns"]
        cooldowns_col.update_one(
            {"guild_id": guild_id, "user_id": user_id, "action_type": action_type},
            {
                "$set": {
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "action_type": action_type,
                    "last_action": datetime.utcnow()
                }
            },
            upsert=True
        )

    def _get_cooldown_remaining(self, guild_id: int, user_id: int, action_type: str, cooldown_hours: int):
        """Get remaining cooldown time"""
        cooldowns_col = self.bot.db["demographic_cooldowns"]
        cooldown_record = cooldowns_col.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "action_type": action_type
        })

        if not cooldown_record:
            return None

        last_action = cooldown_record["last_action"]
        cooldown_end = last_action + timedelta(hours=cooldown_hours)
        remaining = cooldown_end - datetime.utcnow()

        if remaining.total_seconds() <= 0:
            return None

        return remaining

    def _update_demographic_points(self, collection, guild_id: int, user_id: int, demographic: str, points_gained: float, state: str):
        """Update demographic points for a candidate and handle backlash"""
        # Initialize demographic_points if it doesn't exist
        collection.update_one(
            {"guild_id": guild_id, "winners.user_id": user_id},
            {"$set": {"winners.$.demographic_points": {}}},
            upsert=False
        )

        # Get current demographic points
        winners_config = collection.find_one({"guild_id": guild_id})
        candidate = None
        for winner in winners_config.get("winners", []):
            if winner["user_id"] == user_id:
                candidate = winner
                break

        if not candidate:
            return

        current_demographics = candidate.get("demographic_points", {})
        current_points = current_demographics.get(demographic, 0)
        new_points = current_points + points_gained

        # Check threshold and calculate backlash
        threshold = DEMOGRAPHIC_THRESHOLDS.get(demographic, 20)
        backlash_updates = {}

        # Early soft backlash when approaching threshold (90% of threshold)
        early_backlash_threshold = threshold * 0.9
        # Medium backlash when exceeding threshold (125% of threshold)
        medium_backlash_threshold = threshold * 1.25 
        # Hard backlash at 150% of threshold
        hard_backlash_threshold = threshold * 1.5  

        if new_points > hard_backlash_threshold:
            backlash_loss = -2.0  # Hard backlash
            opposing_blocs = DEMOGRAPHIC_CONFLICTS.get(demographic, [])
            for opposing_bloc in opposing_blocs:
                current_opposing = current_demographics.get(opposing_bloc, 0)
                backlash_updates[f"winners.$.demographic_points.{opposing_bloc}"] = max(0, current_opposing + backlash_loss)
        elif new_points > medium_backlash_threshold:
            backlash_loss = -1.0  # Medium backlash
            opposing_blocs = DEMOGRAPHIC_CONFLICTS.get(demographic, [])
            for opposing_bloc in opposing_blocs:
                current_opposing = current_demographics.get(opposing_bloc, 0)
                backlash_updates[f"winners.$.demographic_points.{opposing_bloc}"] = max(0, current_opposing + backlash_loss)
        elif new_points > early_backlash_threshold and current_points <= early_backlash_threshold:
            backlash_loss = -0.5  # Early soft backlash (only triggers when crossing the threshold)
            opposing_blocs = DEMOGRAPHIC_CONFLICTS.get(demographic, [])
            for opposing_bloc in opposing_blocs:
                current_opposing = current_demographics.get(opposing_bloc, 0)
                backlash_updates[f"winners.$.demographic_points.{opposing_bloc}"] = max(0, current_opposing + backlash_loss)


        # Apply state multiplier
        state_multiplier = self.STATE_DEMOGRAPHICS.get(state.upper(), {}).get(demographic, 1.0)
        final_points_gained = points_gained * state_multiplier

        # Update the demographic points
        update_doc = {
            f"winners.$.demographic_points.{demographic}": current_points + final_points_gained
        }
        update_doc.update(backlash_updates)

        collection.update_one(
            {"guild_id": guild_id, "winners.user_id": user_id},
            {"$set": update_doc}
        )

        return final_points_gained, backlash_updates

    class DemographicSpeechModal(discord.ui.Modal, title='Demographic Campaign Speech'):
        def __init__(self, target_candidate: str, state_name: str, demographic: str):
            super().__init__()
            self.target_candidate = target_candidate
            self.state_name = state_name
            self.demographic = demographic

        speech_text = discord.ui.TextInput(
            label='Demographic Speech Content',
            style=discord.TextStyle.long,
            placeholder='Enter your targeted demographic speech (400-2000 characters)...',
            min_length=400,
            max_length=2000
        )

        async def on_submit(self, interaction: discord.Interaction):
            # Get the cog instance
            cog = interaction.client.get_cog('Demographics')

            # Process the speech
            await cog._process_demographic_speech(interaction, str(self.speech_text), self.target_candidate, self.state_name, self.demographic)

    async def _process_demographic_speech(self, interaction: discord.Interaction, speech_text: str, target_name: str, state_name: str, demographic: str):
        """Process demographic speech submission"""
        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate in the General Campaign to give demographic speeches.",
                ephemeral=True
            )
            return

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target_name)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target_name}' not found.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate["stamina"] < 2.0:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a demographic speech! They need at least 2.0 stamina.",
                ephemeral=True
            )
            return

        # Calculate base points (0.5-1.5 based on content length)
        char_count = len(speech_text)
        base_points = (char_count / 1000) * 1.0
        base_points = min(base_points, 1.5)

        # Update demographic points and handle backlash
        points_gained, backlash_updates = self._update_demographic_points(
            target_signups_col, interaction.guild.id, target_candidate["user_id"], 
            demographic, base_points, state_name
        )

        # Update stamina
        target_signups_col.update_one(
            {"guild_id": interaction.guild.id, "winners.user_id": target_candidate["user_id"]},
            {"$inc": {"winners.$.stamina": -2.0}}
        )

        embed = discord.Embed(
            title="🎤 Demographic Campaign Speech",
            description=f"**{candidate['name']}** gives a targeted speech to **{demographic}** supporting **{target_candidate['name']}** in {state_name}!",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Truncate speech for display if too long
        display_speech = speech_text
        if len(display_speech) > 800:
            display_speech = display_speech[:797] + "..."

        embed.add_field(
            name="📜 Speech Content",
            value=display_speech,
            inline=False
        )

        # Show demographic progress
        threshold = DEMOGRAPHIC_THRESHOLDS.get(demographic, 20)
        current_points = target_candidate.get("demographic_points", {}).get(demographic, 0) + points_gained
        progress_bar = "█" * min(int((current_points / threshold) * 10), 10) + "░" * max(0, 10 - int((current_points / threshold) * 10))

        embed.add_field(
            name="📊 Demographic Impact",
            value=f"**Target Demographic:** {demographic}\n"
                  f"**State:** {state_name}\n"
                  f"**Points Gained:** +{points_gained:.2f}\n"
                  f"**Progress:** {progress_bar} {current_points:.1f}/{threshold}\n"
                  f"**Characters:** {char_count:,}",
            inline=True
        )

        # Show backlash if any
        if backlash_updates:
            backlash_text = ""
            for key, value in backlash_updates.items():
                bloc_name = key.split('.')[-1]
                backlash_text += f"**{bloc_name}:** -{abs(value - target_candidate.get('demographic_points', {}).get(bloc_name, 0)):.1f}\n"

            embed.add_field(
                name="⚖️ Backlash Effects",
                value=backlash_text,
                inline=True
            )

        embed.set_footer(text="Next demographic speech available in 8 hours")

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="demographic_speech",
        description="Give a targeted demographic speech in a U.S. state (General Campaign only)"
    )
    @app_commands.describe(
        state="U.S. state for demographic speech",
        demographic="Target demographic group",
        target="The presidential candidate who will receive benefits (optional)"
    )
    async def demographic_speech(self, interaction: discord.Interaction, state: str, demographic: str, target: Optional[str] = None):
        # Check if in General Campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") != "General Campaign":
            await interaction.response.send_message(
                "❌ Demographic speeches can only be given during the General Campaign phase.",
                ephemeral=True
            )
            return

        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Validate demographic
        if demographic not in DEMOGRAPHIC_THRESHOLDS:
            await interaction.response.send_message(
                f"❌ Invalid demographic. Please choose from: {', '.join(sorted(DEMOGRAPHIC_THRESHOLDS.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate in the General Campaign to give demographic speeches.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Check cooldown (8 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "demographic_speech", 8):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "demographic_speech", 8)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before giving another demographic speech.",
                ephemeral=True
            )
            return

        # Set cooldown
        self._set_cooldown(interaction.guild.id, interaction.user.id, "demographic_speech")

        # Show modal for speech input
        modal = self.DemographicSpeechModal(target, state_upper, demographic)
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="demographic_poster",
        description="Create a targeted demographic poster in a U.S. state (General Campaign only)"
    )
    @app_commands.describe(
        state="U.S. state for demographic poster",
        demographic="Target demographic group",
        image="Upload your demographic poster image",
        target="The presidential candidate who will receive benefits (optional)"
    )
    async def demographic_poster(
        self, 
        interaction: discord.Interaction, 
        state: str,
        demographic: str,
        image: discord.Attachment,
        target: Optional[str] = None
    ):
        # Check if in General Campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") != "General Campaign":
            await interaction.response.send_message(
                "❌ Demographic posters can only be created during the General Campaign phase.",
                ephemeral=True
            )
            return

        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Validate demographic
        if demographic not in DEMOGRAPHIC_THRESHOLDS:
            await interaction.response.send_message(
                f"❌ Invalid demographic. Please choose from: {', '.join(sorted(DEMOGRAPHIC_THRESHOLDS.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate in the General Campaign to create demographic posters.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate["stamina"] < 1.5:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina! They need at least 1.5 stamina to create a demographic poster.",
                ephemeral=True
            )
            return

        # Check cooldown (6 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "demographic_poster", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "demographic_poster", 6)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before creating another demographic poster.",
                ephemeral=True
            )
            return

        # Check if attachment is an image
        if not image or not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message(
                "❌ Please upload an image file (PNG, JPG, GIF, etc.).",
                ephemeral=True
            )
            return

        # Check file size
        if image.size > 10 * 1024 * 1024:
            await interaction.response.send_message(
                "❌ Image file too large! Maximum size is 10MB.",
                ephemeral=True
            )
            return

        # Random demographic points between 0.3 and 0.8
        base_points = random.uniform(0.3, 0.8)

        # Update demographic points and handle backlash
        points_gained, backlash_updates = self._update_demographic_points(
            target_signups_col, interaction.guild.id, target_candidate["user_id"], 
            demographic, base_points, state_upper
        )

        # Update stamina
        target_signups_col.update_one(
            {"guild_id": interaction.guild.id, "winners.user_id": target_candidate["user_id"]},
            {"$inc": {"winners.$.stamina": -1.5}}
        )

        # Set cooldown
        self._set_cooldown(interaction.guild.id, interaction.user.id, "demographic_poster")

        embed = discord.Embed(
            title="🖼️ Demographic Campaign Poster",
            description=f"**{candidate['name']}** creates targeted materials for **{demographic}** supporting **{target_candidate['name']}** in {state_upper}!",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        # Show demographic progress
        threshold = DEMOGRAPHIC_THRESHOLDS.get(demographic, 20)
        current_points = target_candidate.get("demographic_points", {}).get(demographic, 0) + points_gained
        progress_bar = "█" * min(int((current_points / threshold) * 10), 10) + "░" * max(0, 10 - int((current_points / threshold) * 10))

        embed.add_field(
            name="📊 Demographic Impact",
            value=f"**Target Demographic:** {demographic}\n"
                  f"**State:** {state_upper}\n"
                  f"**Points Gained:** +{points_gained:.2f}\n"
                  f"**Progress:** {progress_bar} {current_points:.1f}/{threshold}\n"
                  f"**Stamina Cost:** -1.5",
            inline=True
        )

        # Show backlash if any
        if backlash_updates:
            backlash_text = ""
            for key, value in backlash_updates.items():
                bloc_name = key.split('.')[-1]
                backlash_text += f"**{bloc_name}:** -{abs(value - target_candidate.get('demographic_points', {}).get(bloc_name, 0)):.1f}\n"

            embed.add_field(
                name="⚖️ Backlash Effects",
                value=backlash_text,
                inline=True
            )

        embed.add_field(
            name="📍 Distribution",
            value=f"Targeted distribution to {demographic}\nthroughout {state_upper}",
            inline=True
        )

        embed.set_footer(text="Next demographic poster available in 6 hours")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="demographic_ad",
        description="Create a targeted demographic video ad in a U.S. state (General Campaign only)"
    )
    @app_commands.describe(
        state="U.S. state for demographic ad",
        demographic="Target demographic group",
        target="The presidential candidate who will receive benefits (optional)"
    )
    async def demographic_ad(self, interaction: discord.Interaction, state: str, demographic: str, target: Optional[str] = None):
        # Check if in General Campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") != "General Campaign":
            await interaction.response.send_message(
                "❌ Demographic ads can only be created during the General Campaign phase.",
                ephemeral=True
            )
            return

        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Validate demographic
        if demographic not in DEMOGRAPHIC_THRESHOLDS:
            await interaction.response.send_message(
                f"❌ Invalid demographic. Please choose from: {', '.join(sorted(DEMOGRAPHIC_THRESHOLDS.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate in the General Campaign to create demographic ads.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate["stamina"] < 2.5:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina! They need at least 2.5 stamina to create a demographic ad.",
                ephemeral=True
            )
            return

        # Check cooldown (10 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "demographic_ad", 10):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "demographic_ad", 10)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before creating another demographic ad.",
                ephemeral=True
            )
            return

        # Send initial message asking for video
        await interaction.response.send_message(
            f"📺 **{candidate['name']}**, please reply to this message with your demographic campaign video!\n\n"
            f"**Target:** {target_candidate['name']}\n"
            f"**Demographic:** {demographic}\n"
            f"**State:** {state_upper}\n"
            f"**Requirements:**\n"
            f"• Video file (MP4, MOV, AVI, etc.)\n"
            f"• Maximum size: 25MB\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** 0.8-1.5 demographic points, -2.5 stamina",
            ephemeral=False
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id and
                    len(message.attachments) > 0)

        try:
            # Wait for user to reply with attachment
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            video = reply_message.attachments[0]

            # Check if attachment is a video
            if not video.content_type or not video.content_type.startswith('video/'):
                await reply_message.reply("❌ Please upload a video file (MP4 format preferred).")
                return

            # Check file size
            if video.size > 25 * 1024 * 1024:
                await reply_message.reply("❌ Video file too large! Maximum size is 25MB.")
                return

            # Random demographic points between 0.8 and 1.5
            base_points = random.uniform(0.8, 1.5)

            # Update demographic points and handle backlash
            points_gained, backlash_updates = self._update_demographic_points(
                target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                demographic, base_points, state_upper
            )

            # Update stamina
            target_signups_col.update_one(
                {"guild_id": interaction.guild.id, "winners.user_id": target_candidate["user_id"]},
                {"$inc": {"winners.$.stamina": -2.5}}
            )

            # Set cooldown
            self._set_cooldown(interaction.guild.id, interaction.user.id, "demographic_ad")

            embed = discord.Embed(
                title="📺 Demographic Campaign Video Ad",
                description=f"**{candidate['name']}** creates a targeted advertisement for **{demographic}** supporting **{target_candidate['name']}** in {state_upper}!",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            # Show demographic progress
            threshold = DEMOGRAPHIC_THRESHOLDS.get(demographic, 20)
            current_points = target_candidate.get("demographic_points", {}).get(demographic, 0) + points_gained
            progress_bar = "█" * min(int((current_points / threshold) * 10), 10) + "░" * max(0, 10 - int((current_points / threshold) * 10))

            embed.add_field(
                name="📊 Ad Performance",
                value=f"**Target Demographic:** {demographic}\n"
                      f"**State:** {state_upper}\n"
                      f"**Points Gained:** +{points_gained:.2f}\n"
                      f"**Progress:** {progress_bar} {current_points:.1f}/{threshold}\n"
                      f"**Stamina Cost:** -2.5",
                inline=True
            )

            # Show backlash if any
            if backlash_updates:
                backlash_text = ""
                for key, value in backlash_updates.items():
                    bloc_name = key.split('.')[-1]
                    backlash_text += f"**{bloc_name}:** -{abs(value - target_candidate.get('demographic_points', {}).get(bloc_name, 0)):.1f}\n"

                embed.add_field(
                    name="⚖️ Backlash Effects",
                    value=backlash_text,
                    inline=True
                )

            embed.add_field(
                name="📱 Targeted Reach",
                value=f"Broadcast to {demographic}\nacross {state_upper} media networks",
                inline=True
            )

            embed.set_footer(text="Next demographic ad available in 10 hours")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate['name']}**, your demographic ad creation timed out. Please use `/demographic_ad` again and reply with your video within 5 minutes."
            )

    # Autocomplete functions
    @demographic_speech.autocomplete("state")
    async def state_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @demographic_poster.autocomplete("state")
    async def state_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @demographic_ad.autocomplete("state")
    async def state_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @demographic_speech.autocomplete("demographic")
    async def demographic_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        demographics = list(DEMOGRAPHIC_THRESHOLDS.keys())
        return [app_commands.Choice(name=demo, value=demo)
                for demo in demographics if current.lower() in demo.lower()][:25]

    @demographic_poster.autocomplete("demographic")
    async def demographic_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        demographics = list(DEMOGRAPHIC_THRESHOLDS.keys())
        return [app_commands.Choice(name=demo, value=demo)
                for demo in demographics if current.lower() in demo.lower()][:25]

    @demographic_ad.autocomplete("demographic")
    async def demographic_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        demographics = list(DEMOGRAPHIC_THRESHOLDS.keys())
        return [app_commands.Choice(name=demo, value=demo)
                for demo in demographics if current.lower() in demo.lower()][:25]

    @app_commands.command(
        name="demographic_status",
        description="View your demographic voting bloc progress and thresholds"
    )
    async def demographic_status(self, interaction: discord.Interaction):
        # Check if user is a presidential candidate in General Campaign
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate in the General Campaign to view demographic status.",
                ephemeral=True
            )
            return

        candidate_name = candidate["name"]
        current_demographics = candidate.get("demographic_points", {})

        embed = discord.Embed(
            title="📊 Demographic Voting Bloc Status",
            description=f"**{candidate_name}** ({candidate['party']}) - General Campaign Progress",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        # Group demographics by category for better display
        high_priority = []
        medium_priority = []
        low_priority = []

        for demographic, threshold in DEMOGRAPHIC_THRESHOLDS.items():
            current_points = current_demographics.get(demographic, 0)
            progress_percent = (current_points / threshold) * 100
            progress_bar = "█" * min(int(progress_percent / 10), 10) + "░" * max(0, 10 - int(progress_percent / 10))

            status_line = f"**{demographic}**\n{progress_bar} {current_points:.1f}/{threshold} ({progress_percent:.1f}%)\n"

            if threshold >= 20:
                high_priority.append(status_line)
            elif threshold >= 15:
                medium_priority.append(status_line)
            else:
                low_priority.append(status_line)

        if high_priority:
            embed.add_field(
                name="🎯 High-Value Demographics (20+ points)",
                value="".join(high_priority),
                inline=False
            )

        if medium_priority:
            embed.add_field(
                name="📈 Medium-Value Demographics (15-19 points)",
                value="".join(medium_priority),
                inline=False
            )

        if low_priority:
            embed.add_field(
                name="📊 Lower-Value Demographics (12-14 points)",
                value="".join(low_priority),
                inline=False
            )

        # Show completed demographics
        completed = [demo for demo, threshold in DEMOGRAPHIC_THRESHOLDS.items() 
                    if current_demographics.get(demo, 0) >= threshold]

        if completed:
            embed.add_field(
                name="✅ Completed Demographics",
                value="\n".join(f"• {demo}" for demo in completed),
                inline=True
            )

        # Show cooldown status
        cooldown_info = ""
        cooldowns = [
            ("demographic_speech", 8),
            ("demographic_poster", 6),
            ("demographic_ad", 10)
        ]

        for action, hours in cooldowns:
            if not self._check_cooldown(interaction.guild.id, interaction.user.id, action, hours):
                remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, action, hours)
                hours_left = int(remaining.total_seconds() // 3600)
                minutes_left = int((remaining.total_seconds() % 3600) // 60)
                cooldown_info += f"🔒 **{action.replace('_', ' ').title()}:** {hours_left}h {minutes_left}m\n"
            else:
                cooldown_info += f"✅ **{action.replace('_', ' ').title()}:** Available\n"

        embed.add_field(
            name="⏱️ Action Availability",
            value=cooldown_info,
            inline=True
        )

        # Add warning about backlash
        embed.add_field(
            name="⚠️ Backlash Warning",
            value="Backlash occurs at 90% (soft), 125% (medium), and 150% (hard) of a demographic's threshold!",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Admin Configuration Commands
    @app_commands.command(
        name="admin_demo_overview",
        description="[ADMIN] View all candidates' demographic progress"
    )
    @app_commands.default_permissions(administrator=True)
    async def admin_demographic_overview(self, interaction: discord.Interaction):
        # Check if in General Campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") != "General Campaign":
            await interaction.response.send_message(
                "❌ Demographic overview is only available during the General Campaign phase.",
                ephemeral=True
            )
            return

        winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)

        if not winners_config or not winners_config.get("winners"):
            await interaction.response.send_message(
                "❌ No presidential candidates found for the General Campaign.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="👑 Admin Demographic Overview",
            description="All presidential candidates' demographic progress",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        current_year = time_config["current_rp_date"].year if time_config else 2024
        primary_year = current_year - 1 if current_year % 2 == 0 else current_year

        # Get all primary winners
        presidential_candidates = []
        for winner in winners_config.get("winners", []):
            if (winner.get("primary_winner", False) and 
                winner["year"] == primary_year and
                winner["office"] in ["President", "Vice President"]):
                presidential_candidates.append(winner)

        if not presidential_candidates:
            await interaction.response.send_message(
                "❌ No primary winners found for the General Campaign.",
                ephemeral=True
            )
            return

        for candidate in presidential_candidates:
            candidate_demographics = candidate.get("demographic_points", {})
            completed_count = sum(1 for demo, threshold in DEMOGRAPHIC_THRESHOLDS.items() 
                                if candidate_demographics.get(demo, 0) >= threshold)

            total_points = sum(candidate_demographics.values())
            stamina = candidate.get("stamina", 0)

            embed.add_field(
                name=f"{candidate['name']} ({candidate['party']})",
                value=f"**Completed Demographics:** {completed_count}/{len(DEMOGRAPHIC_THRESHOLDS)}\n"
                      f"**Total Points:** {total_points:.1f}\n"
                      f"**Stamina:** {stamina:.1f}",
                inline=True
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_demo_reset",
        description="[ADMIN] Reset all demographic progress for a candidate"
    )
    @app_commands.describe(candidate_name="Name of the candidate to reset")
    @app_commands.default_permissions(administrator=True)
    async def admin_demographic_reset(self, interaction: discord.Interaction, candidate_name: str):
        winners_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, candidate_name)

        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Presidential candidate '{candidate_name}' not found.",
                ephemeral=True
            )
            return

        # Reset all demographic points
        winners_col.update_one(
            {"guild_id": interaction.guild.id, "winners.user_id": target_candidate["user_id"]},
            {"$set": {"winners.$.demographic_points": {}}}
        )

        embed = discord.Embed(
            title="🔄 Demographic Reset Complete",
            description=f"**{target_candidate['name']}**'s demographic progress has been reset.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Reset Details",
            value=f"**Candidate:** {target_candidate['name']}\n"
                  f"**Party:** {target_candidate['party']}\n"
                  f"**Action:** All demographic points set to 0",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_demo_modify",
        description="[ADMIN] Modify demographic points for a candidate"
    )
    @app_commands.describe(
        candidate_name="Name of the candidate",
        demographic="Demographic to modify",
        points="Points to set (use negative values to subtract)"
    )
    @app_commands.default_permissions(administrator=True)
    async def admin_demographic_modify(self, interaction: discord.Interaction, candidate_name: str, demographic: str, points: float):
        if demographic not in DEMOGRAPHIC_THRESHOLDS:
            await interaction.response.send_message(
                f"❌ Invalid demographic. Choose from: {', '.join(sorted(DEMOGRAPHIC_THRESHOLDS.keys()))}",
                ephemeral=True
            )
            return

        winners_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, candidate_name)

        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Presidential candidate '{candidate_name}' not found.",
                ephemeral=True
            )
            return

        # Get current points
        current_demographics = target_candidate.get("demographic_points", {})
        current_points = current_demographics.get(demographic, 0)
        new_points = max(0, points)  # Ensure points don't go below 0

        # Update the demographic points
        winners_col.update_one(
            {"guild_id": interaction.guild.id, "winners.user_id": target_candidate["user_id"]},
            {"$set": {f"winners.$.demographic_points.{demographic}": new_points}}
        )

        threshold = DEMOGRAPHIC_THRESHOLDS.get(demographic, 20)
        progress_percent = (new_points / threshold) * 100
        progress_bar = "█" * min(int(progress_percent / 10), 10) + "░" * max(0, 10 - int(progress_percent / 10))

        embed = discord.Embed(
            title="⚙️ Demographic Points Modified",
            description=f"**{target_candidate['name']}**'s {demographic} points have been modified.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Modification Details",
            value=f"**Candidate:** {target_candidate['name']}\n"
                  f"**Demographic:** {demographic}\n"
                  f"**Previous Points:** {current_points:.1f}\n"
                  f"**New Points:** {new_points:.1f}\n"
                  f"**Progress:** {progress_bar} {new_points:.1f}/{threshold}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_demo_clear_cooldowns",
        description="[ADMIN] Clear all demographic cooldowns for a user"
    )
    @app_commands.describe(user="User whose cooldowns to clear")
    @app_commands.default_permissions(administrator=True)
    async def admin_demographic_clear_cooldowns(self, interaction: discord.Interaction, user: discord.Member):
        cooldowns_col = self.bot.db["demographic_cooldowns"]

        result = cooldowns_col.delete_many({
            "guild_id": interaction.guild.id,
            "user_id": user.id
        })

        embed = discord.Embed(
            title="🕒 Cooldowns Cleared",
            description=f"All demographic cooldowns cleared for **{user.display_name}**.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Action Details",
            value=f"**Target User:** {user.mention}\n"
                  f"**Cooldowns Removed:** {result.deleted_count}\n"
                  f"**Status:** All demographic actions now available",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="view_state_demographics",
        description="View demographic strengths for a specific state or all states"
    )
    @app_commands.describe(
        state_name="View specific state demographics (optional - shows all if not specified)"
    )
    async def view_state_demographics(self, interaction: discord.Interaction, state_name: str = None):
        """View demographic strengths by state"""
        if state_name:
            state_name = state_name.upper()
            if state_name not in self.STATE_DEMOGRAPHICS:
                await interaction.response.send_message(
                    f"❌ State '{state_name}' not found. Please choose from: {', '.join(sorted(self.STATE_DEMOGRAPHICS.keys()))}",
                    ephemeral=False
                )
                return

            state_data = self.STATE_DEMOGRAPHICS[state_name]

            embed = discord.Embed(
                title=f"📊 {state_name} Demographic Strengths",
                description="Demographic voting bloc influence levels in this state",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Group demographics by strength
            strong_demos = []
            moderate_demos = []
            small_demos = []

            for demographic, strength in state_data.items():
                if strength == 1.75:
                    strong_demos.append(demographic)
                elif strength == 0.75:
                    moderate_demos.append(demographic)
                elif strength == 0.3:
                    small_demos.append(demographic)

            if strong_demos:
                embed.add_field(
                    name="🔥 Strong Demographics (1.75x multiplier)",
                    value="\n".join(f"• {demo}" for demo in strong_demos),
                    inline=False
                )

            if moderate_demos:
                embed.add_field(
                    name="📈 Moderate Demographics (0.75x multiplier)",
                    value="\n".join(f"• {demo}" for demo in moderate_demos),
                    inline=False
                )

            if small_demos:
                embed.add_field(
                    name="📉 Small Demographics (0.3x multiplier)",
                    value="\n".join(f"• {demo}" for demo in small_demos),
                    inline=False
                )

            embed.add_field(
                name="ℹ️ How to Use",
                value="Use demographic campaigns in this state to get the listed multipliers!\n"
                      "Strong demographics give the best point gains.",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=False)

        else:
            # Show summary of all states
            embed = discord.Embed(
                title="🗺️ All States - Demographic Overview",
                description="Summary of strong demographics by state",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            # Create a summary showing which states have strong demographics
            demo_summary = {}

            for state, demographics in self.STATE_DEMOGRAPHICS.items():
                for demo, strength in demographics.items():
                    if strength == 1.75:  # Only show strong demographics
                        if demo not in demo_summary:
                            demo_summary[demo] = []
                        demo_summary[demo].append(state)

            # Sort demographics by how many states they're strong in
            sorted_demos = sorted(demo_summary.items(), key=lambda x: len(x[1]), reverse=True)

            field_count = 0
            for demographic, states in sorted_demos[:15]:  # Limit to top 15 to avoid embed limits
                if field_count >= 24:  # Discord embed field limit
                    break

                states_text = ", ".join(states[:8])  # Limit states shown
                if len(states) > 8:
                    states_text += f" (+{len(states) - 8} more)"

                embed.add_field(
                    name=f"🔥 {demographic}",
                    value=f"**Strong in {len(states)} states:**\n{states_text}",
                    inline=True
                )
                field_count += 1

            embed.add_field(
                name="💡 Pro Tip",
                value="Use `/view_state_demographics state_name:<STATE>` to see detailed demographics for a specific state!",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(
        name="admin_demo_system_status",
        description="[ADMIN] View demographic system configuration and statistics"
    )
    @app_commands.default_permissions(administrator=True)
    async def admin_demographic_system_status(self, interaction: discord.Interaction):
        # Get system statistics
        cooldowns_col = self.bot.db["demographic_cooldowns"]
        active_cooldowns = cooldowns_col.count_documents({"guild_id": interaction.guild.id})

        # Get demographic configuration
        embed = discord.Embed(
            title="⚙️ Demographic System Status",
            description="Current system configuration and statistics",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        # System configuration
        config_text = f"**Total Demographics:** {len(DEMOGRAPHIC_THRESHOLDS)}\n"
        config_text += f"**Active Cooldowns:** {active_cooldowns}\n"
        config_text += f"**State Configurations:** {len(self.STATE_DEMOGRAPHICS)}\n"
        config_text += f"**Conflict Pairs:** {len(DEMOGRAPHIC_CONFLICTS)}"

        embed.add_field(
            name="📊 System Configuration",
            value=config_text,
            inline=True
        )

        # Cooldown settings
        cooldown_text = "**Speech:** 8 hours\n"
        cooldown_text += "**Poster:** 6 hours\n"
        cooldown_text += "**Video Ad:** 10 hours"

        embed.add_field(
            name="⏱️ Cooldown Settings",
            value=cooldown_text,
            inline=True
        )

        # Point ranges
        points_text = "**Speech:** 0.5-1.5 (length-based)\n"
        points_text += "**Poster:** 0.3-0.8 (random)\n"
        points_text += "**Video Ad:** 0.8-1.5 (random)"

        embed.add_field(
            name="🎯 Point Ranges",
            value=points_text,
            inline=True
        )

        # Stamina costs
        stamina_text = "**Speech:** -2.0\n"
        stamina_text += "**Poster:** -1.5\n"
        stamina_text += "**Video Ad:** -2.5"

        embed.add_field(
            name="💪 Stamina Costs",
            value=stamina_text,
            inline=True
        )

        # Backlash thresholds
        backlash_text = "**Early Soft Backlash:** 90% of threshold (-0.5)\n"
        backlash_text += "**Medium Backlash:** 125% of threshold (-1.0)\n"
        backlash_text += "**Hard Backlash:** 150% of threshold (-2.0)"

        embed.add_field(
            name="⚖️ Backlash System",
            value=backlash_text,
            inline=True
        )

        # State multipliers
        multiplier_text = "**Small:** 0.3x multiplier\n"
        multiplier_text += "**Moderate:** 0.75x multiplier\n"
        multiplier_text += "**Strong:** 1.75x multiplier"

        embed.add_field(
            name="🗺️ State Multipliers",
            value=multiplier_text,
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Autocomplete for admin commands
    @admin_demographic_reset.autocomplete("candidate_name")
    async def candidate_autocomplete_reset(self, interaction: discord.Interaction, current: str):
        winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)

        if not winners_config:
            return []

        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_year = time_config["current_rp_date"].year if time_config else 2024
        primary_year = current_year - 1 if current_year % 2 == 0 else current_year

        candidates = []
        for winner in winners_config.get("winners", []):
            if (winner.get("primary_winner", False) and 
                winner["year"] == primary_year and
                winner["office"] in ["President", "Vice President"] and
                current.lower() in winner["name"].lower()):
                candidates.append(app_commands.Choice(name=winner["name"], value=winner["name"]))

        return candidates[:25]

    @admin_demographic_modify.autocomplete("candidate_name")
    async def candidate_autocomplete_modify(self, interaction: discord.Interaction, current: str):
        return await self.candidate_autocomplete_reset(interaction, current)

    @admin_demographic_modify.autocomplete("demographic")
    async def demographic_autocomplete_modify(self, interaction: discord.Interaction, current: str):
        demographics = list(DEMOGRAPHIC_THRESHOLDS.keys())
        return [app_commands.Choice(name=demo, value=demo)
                for demo in demographics if current.lower() in demo.lower()][:25]

    @view_state_demographics.autocomplete("state_name")
    async def state_autocomplete_demographics(self, interaction: discord.Interaction, current: str):
        states = list(self.STATE_DEMOGRAPHICS.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

async def setup(bot):
    await bot.add_cog(Demographics(bot))