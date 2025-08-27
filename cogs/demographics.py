import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import asyncio
import random
from typing import Optional, Dict
from .presidential_winners import PRESIDENTIAL_STATE_DATA

# Demographic voting bloc strength values (removed thresholds)
DEMOGRAPHIC_STRENGTH = {
    "Urban Voters": True,
    "Suburban Voters": True,
    "Rural Voters": True,
    "Evangelical Christians": True,
    "African American Voters": True,
    "Latino/Hispanic Voters": True,
    "Asian American Voters": True,
    "Blue-Collar / Working-Class Voters": True,
    "College-Educated Professionals": True,
    "Young Voters (18–29)": True,
    "Senior Citizens (65+)": True,
    "Native American Voters": True,
    "Military & Veteran Voters": True,
    "LGBTQ+ Voters": True,
    "Immigrant Communities": True,
    "Tech & Innovation Workers": True,
    "Wealthy / High-Income Voters": True,
    "Low-Income Voters": True,
    "Environmental & Green Voters": True,
    "Gun Rights Advocates": True
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
            "Small": 0.05,
            "Moderate": 0.10,
            "Strong": 0.25
        }
        return strength_map.get(strength, 0.10)  # Default to moderate

    # State demographic strengths based on actual data
    # Small = 0.05, Moderate = 0.10, Strong = 0.25
    STATE_DEMOGRAPHICS = {
        "ALABAMA": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.25, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.05,
            "Young Voters (18–29)": 0.05, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.05, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.05, "Wealthy / High-Income Voters": 0.05, "Low-Income Voters": 0.25,
            "Environmental & Green Voters": 0.05, "Gun Rights Advocates": 0.25
        },
        "ALASKA": {
            "Urban Voters": 0.05, "Suburban Voters": 0.05, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.05, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "ARIZONA": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.05, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.25, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "ARKANSAS": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.25, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.05,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.05, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.05, "Wealthy / High-Income Voters": 0.05, "Low-Income Voters": 0.25,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "CALIFORNIA": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.05,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.05, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.05,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.05
        },
        "COLORADO": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.10
        },
        "CONNECTICUT": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.05,
            "Evangelical Christians": 0.05, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.05,
            "Military & Veteran Voters": 0.05, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.05,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.05
        },
        "DELAWARE": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.25, "Native American Voters": 0.05,
            "Military & Veteran Voters": 0.05, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "FLORIDA": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.05, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.05, "Senior Citizens (65+)": 0.25, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "GEORGIA": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.25, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.05, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "HAWAII": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.05,
            "Evangelical Christians": 0.05, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.05, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.05
        },
        "IDAHO": {
            "Urban Voters": 0.05, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.25, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "ILLINOIS": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "INDIANA": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "IOWA": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "KANSAS": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "KENTUCKY": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.25, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.05,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.05, "Low-Income Voters": 0.25,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "LOUISIANA": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.25, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.05,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.05, "Low-Income Voters": 0.25,
            "Environmental & Green Voters": 0.05, "Gun Rights Advocates": 0.10
        },
        "MAINE": {
            "Urban Voters": 0.05, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.05,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.05, "Senior Citizens (65+)": 0.25, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.05,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.10
        },
        "MARYLAND": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.05,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.05,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.05
        },
        "MASSACHUSETTS": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.05,
            "Evangelical Christians": 0.05, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.05,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.05,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.05
        },
        "MICHIGAN": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "MINNESOTA": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "MISSISSIPPI": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.25, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.05,
            "Young Voters (18–29)": 0.05, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.05, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.05, "Wealthy / High-Income Voters": 0.05, "Low-Income Voters": 0.25,
            "Environmental & Green Voters": 0.05, "Gun Rights Advocates": 0.25
        },
        "MISSOURI": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.25, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "MONTANA": {
            "Urban Voters": 0.05, "Suburban Voters": 0.05, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.05,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.05, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.25, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.05,
            "Tech & Innovation Workers": 0.05, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "NEBRASKA": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "NEVADA": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.05,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.05, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "NEW HAMPSHIRE": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "NEW JERSEY": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.05,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.05,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.05,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.05
        },
        "NEW MEXICO": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.05, "Low-Income Voters": 0.25,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.10
        },
        "NEW YORK": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.05
        },
        "NORTH CAROLINA": {
            "Urban Voters": 0.10, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.25, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "NORTH DAKOTA": {
            "Urban Voters": 0.05, "Suburban Voters": 0.05, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.05,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.05, "Immigrant Communities": 0.05,
            "Tech & Innovation Workers": 0.05, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.05, "Gun Rights Advocates": 0.25
        },
        "OHIO": {
            "Urban Voters": 0.10, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "OKLAHOMA": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.25,
            "Evangelical Christians": 0.25, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.05,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.05, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.05, "Gun Rights Advocates": 0.25
        },
        "OREGON": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.05, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.10
        },
        "PENNSYLVANIA": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.25, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "RHODE ISLAND": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.05,
            "Evangelical Christians": 0.05, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.05,
            "Military & Veteran Voters": 0.05, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.05
        },
        "SOUTH CAROLINA": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.25, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.25, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "SOUTH DAKOTA": {
            "Urban Voters": 0.05, "Suburban Voters": 0.05, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.05,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.05, "Immigrant Communities": 0.05,
            "Tech & Innovation Workers": 0.05, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "TENNESSEE": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.25, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "TEXAS": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.25, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.25,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.05, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "UTAH": {
            "Urban Voters": 0.10, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.05, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.25
        },
        "VERMONT": {
            "Urban Voters": 0.05, "Suburban Voters": 0.05, "Rural Voters": 0.25,
            "Evangelical Christians": 0.05, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.05,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.05, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.05,
            "Military & Veteran Voters": 0.05, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.05,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.10
        },
        "VIRGINIA": {
            "Urban Voters": 0.25, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.25, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.25, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.05,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "WASHINGTON": {
            "Urban Voters": 0.25, "Suburban Voters": 0.10, "Rural Voters": 0.10,
            "Evangelical Christians": 0.05, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.25, "Blue-Collar / Working-Class Voters": 0.10, "College-Educated Professionals": 0.25,
            "Young Voters (18–29)": 0.25, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.25, "Immigrant Communities": 0.25,
            "Tech & Innovation Workers": 0.25, "Wealthy / High-Income Voters": 0.25, "Low-Income Voters": 0.05,
            "Environmental & Green Voters": 0.25, "Gun Rights Advocates": 0.10
        },
        "WEST VIRGINIA": {
            "Urban Voters": 0.05, "Suburban Voters": 0.05, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.05,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.05,
            "Young Voters (18–29)": 0.05, "Senior Citizens (65+)": 0.25, "Native American Voters": 0.05,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.05, "Immigrant Communities": 0.05,
            "Tech & Innovation Workers": 0.05, "Wealthy / High-Income Voters": 0.05, "Low-Income Voters": 0.25,
            "Environmental & Green Voters": 0.05, "Gun Rights Advocates": 0.25
        },
        "WISCONSIN": {
            "Urban Voters": 0.10, "Suburban Voters": 0.25, "Rural Voters": 0.10,
            "Evangelical Christians": 0.10, "African American Voters": 0.10, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.10, "Blue-Collar / Working-Class Voters": 0.25, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.10,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.10,
            "Tech & Innovation Workers": 0.10, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.10, "Gun Rights Advocates": 0.10
        },
        "WYOMING": {
            "Urban Voters": 0.05, "Suburban Voters": 0.05, "Rural Voters": 0.25,
            "Evangelical Christians": 0.10, "African American Voters": 0.05, "Latino/Hispanic Voters": 0.10,
            "Asian American Voters": 0.05, "Blue-Collar / Working-Class Voters": 0.05, "College-Educated Professionals": 0.10,
            "Young Voters (18–29)": 0.10, "Senior Citizens (65+)": 0.10, "Native American Voters": 0.25,
            "Military & Veteran Voters": 0.10, "LGBTQ+ Voters": 0.10, "Immigrant Communities": 0.05,
            "Tech & Innovation Workers": 0.05, "Wealthy / High-Income Voters": 0.10, "Low-Income Voters": 0.10,
            "Environmental & Green Voters": 0.05, "Gun Rights Advocates": 0.25
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

    def _get_user_candidate(self, guild_id: int, user_id: int):
        """Get user's candidate information for any race type"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # First check all_winners collection for general campaign primary winners
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": guild_id})

            if winners_config and isinstance(winners_config, dict):
                for winner in winners_config.get("winners", []):
                    if (isinstance(winner, dict) and 
                        winner.get("user_id") == user_id and 
                        winner.get("primary_winner", False) and 
                        winner.get("year") == current_year and
                        winner.get("office") in ["President", "Vice President"]):
                        return winners_col, winner

            # Also check presidential winners collection for general campaign
            pres_winners_col, pres_winners_config = self._get_presidential_winners_config(guild_id)

            if pres_winners_config and isinstance(pres_winners_config, dict):
                # For general campaign, look for primary winners from the previous year if we're in an even year
                # Or current year if odd year
                primary_year = current_year - 1 if current_year % 2 == 0 else current_year

                for winner in pres_winners_config.get("winners", []):
                    if (isinstance(winner, dict) and 
                        winner.get("user_id") == user_id and 
                        winner.get("primary_winner", False) and 
                        winner.get("year") == primary_year):
                        return pres_winners_col, winner

            # Check presidential signups collection for general campaign candidates
            pres_signups_col = self.bot.db["presidential_signups"]
            pres_signups_config = pres_signups_col.find_one({"guild_id": guild_id})

            if pres_signups_config and isinstance(pres_signups_config, dict):
                for candidate in pres_signups_config.get("candidates", []):
                    if (isinstance(candidate, dict) and 
                        candidate.get("user_id") == user_id and 
                        candidate.get("year") == current_year and
                        candidate.get("office") in ["President", "Vice President"]):
                        return pres_signups_col, candidate

            # Also check signups collection for admin-created general campaign candidates
            signups_col = self.bot.db["signups"]
            signups_config = signups_col.find_one({"guild_id": guild_id})

            if signups_config and isinstance(signups_config, dict):
                for candidate in signups_config.get("candidates", []):
                    if (isinstance(candidate, dict) and 
                        candidate.get("user_id") == user_id and 
                        candidate.get("year") == current_year and
                        candidate.get("phase") == "General Campaign"):
                        return signups_col, candidate

            return None, None
        else:
            return None, None

    def _get_candidate_by_name(self, guild_id: int, candidate_name: str):
        """Get candidate by name for any race type"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # First check all_winners collection for general campaign primary winners
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": guild_id})

            if winners_config and isinstance(winners_config, dict):
                for winner in winners_config.get("winners", []):
                    if (isinstance(winner, dict) and 
                        winner.get("candidate", "").lower() == candidate_name.lower() and 
                        winner.get("primary_winner", False) and 
                        winner.get("year") == current_year and
                        winner.get("office") in ["President", "Vice President"]):
                        return winners_col, winner

            # Also check presidential winners collection for general campaign
            pres_winners_col, pres_winners_config = self._get_presidential_winners_config(guild_id)

            if pres_winners_config and isinstance(pres_winners_config, dict):
                # For general campaign, look for primary winners from the previous year if we're in an even year
                # Or current year if odd year
                primary_year = current_year - 1 if current_year % 2 == 0 else current_year

                for winner in pres_winners_config.get("winners", []):
                    if (isinstance(winner, dict) and 
                        winner.get("name", "").lower() == candidate_name.lower() and 
                        winner.get("primary_winner", False) and 
                        winner.get("year") == primary_year):
                        return pres_winners_col, winner

            # Also check signups collection for admin-created general campaign candidates
            signups_col = self.bot.db["signups"]
            signups_config = signups_col.find_one({"guild_id": guild_id})

            if signups_config and isinstance(signups_config, dict):
                for candidate in signups_config.get("candidates", []):
                    if (isinstance(candidate, dict) and 
                        candidate.get("name", "").lower() == candidate_name.lower() and 
                        candidate.get("year") == current_year and
                        candidate.get("phase") == "General Campaign"):
                        return signups_col, candidate

            return None, None
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

    def _get_relevant_states_for_candidate(self, candidate: dict, state: str):
        """Get relevant states for demographic calculations based on candidate's office"""
        from .ideology import REGIONS, STATE_TO_SEAT

        office = candidate.get("office", "")
        seat_id = candidate.get("seat_id", "")

        # For presidential/VP candidates, all states are relevant
        if office in ["President", "Vice President"]:
            return [state.upper()]

        # For governors, all states in their region are relevant
        elif office == "Governor":
            region_code = seat_id.split("-")[0] if "-" in seat_id else ""
            region_mapping = {
                "CO": "Columbia", "CA": "Cambridge", "AU": "Austin",
                "SU": "Superior", "HL": "Heartland", "YS": "Yellowstone", "PH": "Phoenix"
            }
            region_name = region_mapping.get(region_code)
            if region_name and region_name in REGIONS:
                return REGIONS[region_name]

        # For senators, all states in their region are relevant
        elif office == "Senator":
            region_code = seat_id.split("-")[1] if "-" in seat_id else ""
            region_mapping = {
                "CO": "Columbia", "CA": "Cambridge", "AU": "Austin",
                "SU": "Superior", "HL": "Heartland", "YS": "Yellowstone", "PH": "Phoenix"
            }
            region_name = region_mapping.get(region_code)
            if region_name and region_name in REGIONS:
                return REGIONS[region_name]

        # For representatives, only their specific state is relevant
        elif office == "Representative":
            for state_name, rep_seat in STATE_TO_SEAT.items():
                if rep_seat == seat_id:
                    return [state_name]

        # Default fallback
        return [state.upper()]

    def _get_demographic_leader(self, guild_id: int, demographic: str, state: str):
        """Get the candidate leading in a specific demographic and state"""
        # Get all general campaign candidates
        winners_col, winners_config = self._get_presidential_winners_config(guild_id)
        signups_col = self.bot.db["signups"]
        signups_config = signups_col.find_one({"guild_id": guild_id})

        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024
        primary_year = current_year - 1 if current_year % 2 == 0 else current_year

        all_candidates = []

        # Get presidential winners (primary winners)
        if winners_config and isinstance(winners_config, dict):
            for winner in winners_config.get("winners", []):
                if (isinstance(winner, dict) and 
                    winner.get("primary_winner", False) and 
                    winner.get("year") == primary_year and
                    winner.get("office") in ["President", "Vice President"]):
                    all_candidates.append(winner)

        # Get general campaign signups
        if signups_config and isinstance(signups_config, dict):
            for candidate in signups_config.get("candidates", []):
                if (isinstance(candidate, dict) and 
                    candidate.get("year") == current_year and
                    candidate.get("phase") == "General Campaign"):
                    all_candidates.append(candidate)

        # Find the leader in this demographic
        leader = None
        highest_points = -1

        for candidate in all_candidates:
            # Check if this state is relevant for this candidate
            relevant_states = self._get_relevant_states_for_candidate(candidate, state)
            if state.upper() not in relevant_states:
                continue

            demo_points = candidate.get("demographic_points", {}).get(demographic, 0)
            if demo_points > highest_points:
                highest_points = demo_points
                leader = candidate

        return leader, highest_points

    def _update_demographic_points(self, collection, guild_id: int, user_id: int, demographic: str, points_gained: float, state: str, candidate: dict):
        """Update demographic points for a candidate and handle backlash"""
        # Determine if this is a winners collection or signups collection
        is_winners_collection = "winners" in str(collection.name)
        is_signups_collection = "signups" in str(collection.name)

        if is_winners_collection:
            # Initialize demographic_points if it doesn't exist
            collection.update_one(
                {"guild_id": guild_id, "winners.user_id": user_id},
                {"$set": {"winners.$.demographic_points": {}}},
                upsert=False
            )

            # Get current demographic points
            config = collection.find_one({"guild_id": guild_id})
            current_candidate = None
            for winner in config.get("winners", []):
                if winner["user_id"] == user_id:
                    current_candidate = winner
                    break

            if not current_candidate:
                return 0, {}

            current_demographics = current_candidate.get("demographic_points", {})
            update_path_prefix = "winners.$.demographic_points"
            array_filter = {"guild_id": guild_id, "winners.user_id": user_id}

        elif is_signups_collection:
            # Initialize demographic_points if it doesn't exist for signups
            collection.update_one(
                {"guild_id": guild_id, "candidates.user_id": user_id},
                {"$set": {"candidates.$.demographic_points": {}}},
                upsert=False
            )

            # Get current demographic points
            config = collection.find_one({"guild_id": guild_id})
            current_candidate = None
            for candidate_entry in config.get("candidates", []):
                if candidate_entry["user_id"] == user_id:
                    current_candidate = candidate_entry
                    break

            if not current_candidate:
                return 0, {}

            current_demographics = current_candidate.get("demographic_points", {})
            update_path_prefix = "candidates.$.demographic_points"
            array_filter = {"guild_id": guild_id, "candidates.user_id": user_id}

        else:
            return 0, {}

        # Get relevant states for this candidate's office
        relevant_states = self._get_relevant_states_for_candidate(candidate, state)

        # Check if the state is relevant for this candidate
        if state.upper() not in relevant_states:
            return 0, {}  # No effect if not in relevant states

        current_points = current_demographics.get(demographic, 0)
        new_points = current_points + points_gained

        # Apply state multiplier
        state_multiplier = self.STATE_DEMOGRAPHICS.get(state.upper(), {}).get(demographic, 0.10)
        final_points_gained = points_gained * state_multiplier

        # Calculate backlash (simplified - no threshold dependency)
        backlash_updates = {}
        if new_points > 5:  # Apply backlash when demographic points exceed 5
            backlash_loss = -0.5
            opposing_blocs = DEMOGRAPHIC_CONFLICTS.get(demographic, [])
            for opposing_bloc in opposing_blocs:
                current_opposing = current_demographics.get(opposing_bloc, 0)
                backlash_updates[f"{update_path_prefix}.{opposing_bloc}"] = max(0, current_opposing + backlash_loss)

        # Update the demographic points
        update_doc = {
            f"{update_path_prefix}.{demographic}": current_points + final_points_gained
        }
        update_doc.update(backlash_updates)

        collection.update_one(
            array_filter,
            {"$set": update_doc}
        )

        return final_points_gained, backlash_updates

    def _get_state_demographic_multiplier(self, state: str, demographic: str) -> float:
        """Get the demographic multiplier for a given state and demographic."""
        return self.STATE_DEMOGRAPHICS.get(state.upper(), {}).get(demographic, 0.10)

    def _get_party_demographic_multiplier(self, candidate: dict, state: str, demographic: str) -> float:
        """Get the party multiplier for a candidate's demographic in a state."""
        # Placeholder for party-specific demographic bonuses.
        # This would need to be expanded based on party platforms and demographic alignments.
        # For now, returning a small default bonus if the demographic is somewhat aligned.
        party = candidate.get("party", "").lower()
        multiplier = 0.0

        if party == "republican":
            if demographic in ["Rural Voters", "Evangelical Christians", "Gun Rights Advocates", "Blue-Collar / Working-Class Voters"]:
                multiplier = 0.05
        elif party == "democrat":
            if demographic in ["Urban Voters", "African American Voters", "Latino/Hispanic Voters", "LGBTQ+ Voters", "Environmental & Green Voters", "College-Educated Professionals"]:
                multiplier = 0.05
        elif party == "independent": # Example for an independent party
            if demographic in ["Young Voters (18–29)", "Suburban Voters"]:
                multiplier = 0.03
        
        # Add more party logic as needed

        # Ensure the state also has a non-zero multiplier for this demographic to apply the party bonus
        state_multiplier = self._get_state_demographic_multiplier(state, demographic)
        if state_multiplier > 0:
             return multiplier
        else:
             return 0.0


    def _update_candidate_demographic_points(self, collection, guild_id: int, user_id: int, demographic: str, points_to_add: float):
        """Helper to add points to a candidate's demographic and ensure it doesn't go below zero."""

        update_path = ""
        if "winners" in str(collection.name):
            update_path = f"winners.$.demographic_points.{demographic}"
            array_filter = {"guild_id": guild_id, "winners.user_id": user_id}
        elif "signups" in str(collection.name):
            update_path = f"candidates.$.demographic_points.{demographic}"
            array_filter = {"guild_id": guild_id, "candidates.user_id": user_id}
        else:
            return

        collection.update_one(
            array_filter,
            {"$inc": {update_path: points_to_add}}
        )

        # Ensure points don't go below zero after update
        collection.update_one(
            array_filter,
            {"$max": {update_path: 0}}
        )

    @app_commands.command(
        name="demographic_speech",
        description="Give a targeted demographic speech in a U.S. state (General Campaign only)"
    )
    @app_commands.describe(
        state="U.S. state for demographic speech",
        demographic="Target demographic group",
        target="The candidate who will receive benefits (optional)"
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
        if demographic not in DEMOGRAPHIC_STRENGTH:
            await interaction.response.send_message(
                f"❌ Invalid demographic. Please choose from: {', '.join(sorted(DEMOGRAPHIC_STRENGTH.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate in the General Campaign to give demographic speeches.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Get demographic info
        state_multiplier = self._get_state_demographic_multiplier(state_upper, demographic)
        party_multiplier = self._get_party_demographic_multiplier(target_candidate, state_upper, demographic)
        total_multiplier = state_multiplier + party_multiplier
        leader, highest_points = self._get_demographic_leader(interaction.guild.id, demographic, state_upper)

        # Send initial message asking for speech
        await interaction.response.send_message(
            f"🎯 **{candidate['name']}**, please reply to this message with your demographic-targeted speech!\n\n"
            f"**Target:** {target_candidate['name']} ({target_candidate['party']})\n"
            f"**State:** {state_upper}\n"
            f"**Demographic:** {demographic}\n"
            f"**State Multiplier:** {state_multiplier:.3f}x\n"
            f"**Party Bonus:** +{party_multiplier:.3f}x\n"
            f"**Total Multiplier:** {total_multiplier:.3f}x\n"
            f"**Current Leader:** {leader['name'] if leader else 'None'} ({highest_points:.1f} points)\n"
            f"**Requirements:**\n"
            f"• Speech content (700-3000 characters)\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** 1 point per 200 characters (modified by total multiplier)"
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id)

        try:
            # Wait for user to reply with speech
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            speech_content = reply_message.content
            char_count = len(speech_content)

            # Check character limits
            if char_count < 700 or char_count > 3000:
                await reply_message.reply(f"❌ Demographic speech must be 700-3000 characters. You wrote {char_count} characters.")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "demographic_speech")

            # Calculate demographic points
            base_points = (char_count / 200) * 1.0  # 1 point per 200 characters
            final_points = base_points * total_multiplier

            # Update candidate's demographic progress
            self._update_candidate_demographic_points(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                    demographic, final_points)

            # Get updated demographic status
            updated_candidate = self._get_candidate_by_name(interaction.guild.id, target)[1]
            current_points = updated_candidate.get("demographic_points", {}).get(demographic, 0)

            # Check new leadership status
            new_leader, new_highest_points = self._get_demographic_leader(interaction.guild.id, demographic, state_upper)
            is_now_leader = new_leader and new_leader["user_id"] == target_candidate["user_id"]

            # Create response embed
            embed = discord.Embed(
                title="🎯 Demographic-Targeted Speech",
                description=f"**{candidate['name']}** delivers a targeted speech for **{target_candidate['name']}** in {state_upper}!",
                color=discord.Color.gold() if is_now_leader else discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Truncate speech for display if too long
            display_speech = speech_content
            if len(display_speech) > 1000:
                display_speech = display_speech[:997] + "..."

            embed.add_field(
                name="📜 Speech Content",
                value=display_speech,
                inline=False
            )

            embed.add_field(
                name="🎯 Campaign Details",
                value=f"**Target:** {target_candidate['name']}\n"
                      f"**State:** {state_upper}\n"
                      f"**Demographic:** {demographic}\n"
                      f"**Characters:** {char_count:,}",
                inline=True
            )

            embed.add_field(
                name="📊 Demographic Progress",
                value=f"**Points Gained:** +{final_points:.2f}\n"
                      f"**Total Points:** {current_points:.2f}\n"
                      f"**Leadership:** {'🏆 LEADING!' if is_now_leader else f'Behind leader by {max(0, new_highest_points - current_points):.1f}'}",
                inline=True
            )

            if is_now_leader:
                embed.add_field(
                    name="🏆 New Leader!",
                    value=f"**{target_candidate['name']}** now leads {demographic} in all states where this demographic has influence!",
                    inline=False
                )

            embed.set_footer(text="Next demographic speech available in 8 hours")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate['name']}**, your demographic speech timed out. Please use `/demographic_speech` again and reply with your speech within 5 minutes."
            )

    @app_commands.command(
        name="demographic_poster",
        description="Create a targeted demographic poster in a U.S. state (General Campaign only)"
    )
    @app_commands.describe(
        state="U.S. state for demographic poster",
        demographic="Target demographic group",
        image="Upload your demographic poster image",
        target="The candidate who will receive benefits (optional)"
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
        if demographic not in DEMOGRAPHIC_STRENGTH:
            await interaction.response.send_message(
                f"❌ Invalid demographic. Please choose from: {', '.join(sorted(DEMOGRAPHIC_STRENGTH.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate in the General Campaign to create demographic posters.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
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
            demographic, base_points, state_upper, target_candidate
        )

        # Update stamina
        target_signups_col.update_one(
            {"guild_id": interaction.guild.id, "winners.user_id": target_candidate["user_id"]},
            {"$inc": {"winners.$.stamina": -1.5}}
        )

        # Set cooldown
        self._set_cooldown(interaction.guild.id, interaction.user.id, "demographic_poster")

        # Get leadership status
        leader, highest_points = self._get_demographic_leader(interaction.guild.id, demographic, state_upper)
        current_points = target_candidate.get("demographic_points", {}).get(demographic, 0) + points_gained
        is_leader = leader and leader["user_id"] == target_candidate["user_id"]

        embed = discord.Embed(
            title="🖼️ Demographic Campaign Poster",
            description=f"**{candidate['name']}** creates targeted materials for **{demographic}** supporting **{target_candidate['name']}** in {state_upper}!",
            color=discord.Color.gold() if is_leader else discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        # Get multiplier info for display
        state_multiplier = self._get_state_demographic_multiplier(state_upper, demographic)
        party_multiplier = self._get_party_demographic_multiplier(target_candidate, state_upper, demographic)

        embed.add_field(
            name="📊 Demographic Impact",
            value=f"**Target Demographic:** {demographic}\n"
                  f"**State:** {state_upper}\n"
                  f"**Points Gained:** +{points_gained:.2f}\n"
                  f"**State Multiplier:** {state_multiplier:.2f}x\n"
                  f"**Party Bonus:** +{party_multiplier:.2f}x\n"
                  f"**Total Points:** {current_points:.1f}\n"
                  f"**Leadership:** {'🏆 LEADING!' if is_leader else f'Behind by {max(0, highest_points - current_points):.1f}'}\n"
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
        target="The candidate who will receive benefits (optional)"
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
        if demographic not in DEMOGRAPHIC_STRENGTH:
            await interaction.response.send_message(
                f"❌ Invalid demographic. Please choose from: {', '.join(sorted(DEMOGRAPHIC_STRENGTH.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate in the General Campaign to create demographic ads.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
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
                demographic, base_points, state_upper, target_candidate
            )

            # Update stamina
            target_signups_col.update_one(
                {"guild_id": interaction.guild.id, "winners.user_id": target_candidate["user_id"]},
                {"$inc": {"winners.$.stamina": -2.5}}
            )

            # Set cooldown
            self._set_cooldown(interaction.guild.id, interaction.user.id, "demographic_ad")

            # Get leadership status
            leader, highest_points = self._get_demographic_leader(interaction.guild.id, demographic, state_upper)
            current_points = target_candidate.get("demographic_points", {}).get(demographic, 0) + points_gained
            is_leader = leader and leader["user_id"] == target_candidate["user_id"]

            embed = discord.Embed(
                title="📺 Demographic Campaign Video Ad",
                description=f"**{candidate['name']}** creates a targeted advertisement for **{demographic}** supporting **{target_candidate['name']}** in {state_upper}!",
                color=discord.Color.gold() if is_leader else discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="📊 Ad Performance",
                value=f"**Target Demographic:** {demographic}\n"
                      f"**State:** {state_upper}\n"
                      f"**Points Gained:** +{points_gained:.2f}\n"
                      f"**Total Points:** {current_points:.1f}\n"
                      f"**Leadership:** {'🏆 LEADING!' if is_leader else f'Behind by {max(0, highest_points - current_points):.1f}'}\n"
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
        demographics = list(DEMOGRAPHIC_STRENGTH.keys())
        return [app_commands.Choice(name=demo, value=demo)
                for demo in demographics if current.lower() in demo.lower()][:25]

    @demographic_poster.autocomplete("demographic")
    async def demographic_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        demographics = list(DEMOGRAPHIC_STRENGTH.keys())
        return [app_commands.Choice(name=demo, value=demo)
                for demo in demographics if current.lower() in demo.lower()][:25]

    @demographic_ad.autocomplete("demographic")
    async def demographic_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        demographics = list(DEMOGRAPHIC_STRENGTH.keys())
        return [app_commands.Choice(name=demo, value=demo)
                for demo in demographics if current.lower() in demo.lower()][:25]

    @app_commands.command(
        name="demographic_status",
        description="View your demographic voting bloc progress and leaderboard"
    )
    async def demographic_status(self, interaction: discord.Interaction):
        # Defer response to prevent timeout
        await interaction.response.defer(ephemeral=True)

        try:
            # Check if user is a candidate in General Campaign
            signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

            if not candidate:
                await interaction.followup.send(
                    "❌ You must be a registered candidate in the General Campaign to view demographic status.",
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

            # Get all primary winners
            time_col, time_config = self._get_time_config(interaction.guild.id)
            current_year = time_config["current_rp_date"].year if time_config else 2024
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year

            all_candidates = []
            winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)
            if winners_config:
                winners_data = winners_config.get("winners", [])

                if isinstance(winners_data, list):
                    for winner in winners_data:
                        if (isinstance(winner, dict) and
                            winner.get("primary_winner", False) and 
                            winner.get("year") == primary_year and
                            winner.get("office") in ["President", "Vice President"]):
                            all_candidates.append(winner)
                elif isinstance(winners_data, dict):
                    signups_col, signups_config = self._get_presidential_config(interaction.guild.id)
                    if signups_config:
                        election_year = winners_config.get("election_year", current_year)
                        signup_year = election_year - 1 if election_year % 2 == 0 else election_year

                        for party, winner_name in winners_data.items():
                            if isinstance(winner_name, str):
                                for candidate in signups_config.get("candidates", []):
                                    if (isinstance(candidate, dict) and
                                        candidate.get("name", "").lower() == winner_name.lower() and
                                        candidate.get("year") == signup_year and
                                        candidate.get("office") == "President"):
                                        all_candidates.append(candidate)
                                        break
                elif isinstance(winners_data, str):
                    print(f"Warning: winners_data is a string: {winners_data}")

            if not all_candidates: # Handle case where no candidates are found
                 await interaction.followup.send(
                    "❌ No candidates found for leadership comparison.",
                    ephemeral=True
                )
                 return


            demographics_text = ""
            leading_count = 0

            for demographic in sorted(DEMOGRAPHIC_STRENGTH.keys()):
                current_points = current_demographics.get(demographic, 0)

                highest_points = -1
                is_leading = False

                for other_candidate in all_candidates:
                    other_points = other_candidate.get("demographic_points", {}).get(demographic, 0)
                    if other_points > highest_points:
                        highest_points = other_points
                        is_leading = (other_candidate["user_id"] == candidate["user_id"])
                    elif other_points == highest_points and other_candidate["user_id"] == candidate["user_id"]:
                        is_leading = True

                if is_leading and current_points > 0:
                    leading_count += 1
                    status = "🏆 LEADING"
                else:
                    gap = highest_points - current_points if highest_points > current_points else 0
                    status = f"Behind by {gap:.1f}" if gap > 0 else "Tied for lead"

                demographics_text += f"**{demographic}:** {current_points:.1f} pts ({status})\n"

            if len(demographics_text) > 1024:
                demo_items = [item for item in demographics_text.split('\n') if item.strip()]
                chunk_size = 10
                for i in range(0, len(demo_items), chunk_size):
                    chunk = demo_items[i:i+chunk_size]
                    field_name = f"📊 Demographics ({i//chunk_size + 1})"
                    embed.add_field(
                        name=field_name,
                        value='\n'.join(chunk),
                        inline=False
                    )
            else:
                embed.add_field(
                    name="📊 All Demographics",
                    value=demographics_text,
                    inline=False
                )

            total_points = sum(current_demographics.values())
            embed.add_field(
                name="📈 Summary",
                value=f"**Leading Demographics:** {leading_count}/{len(DEMOGRAPHIC_STRENGTH)}\n"
                      f"**Total Points:** {total_points:.1f}\n"
                      f"**Average per Demo:** {total_points/len(DEMOGRAPHIC_STRENGTH):.1f}",
                inline=True
            )

            cooldown_info = ""
            cooldowns = [
                ("demographic_speech", 8),
                ("demographic_poster", 6),
                ("demographic_ad", 10)
            ]

            for action, hours in cooldowns:
                if not self._check_cooldown(interaction.guild.id, interaction.user.id, action, hours):
                    remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, action, hours)
                    if remaining:
                        hours_left = int(remaining.total_seconds() // 3600)
                        minutes_left = int((remaining.total_seconds() % 3600) // 60)
                        cooldown_info += f"🔒 **{action.replace('_', ' ').title()}:** {hours_left}h {minutes_left}m\n"
                    else:
                        cooldown_info += f"✅ **{action.replace('_', ' ').title()}:** Available\n"
                else:
                    cooldown_info += f"✅ **{action.replace('_', ' ').title()}:** Available\n"

            embed.add_field(
                name="⏱️ Action Availability",
                value=cooldown_info,
                inline=True
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Error in demographic_status: {e}")
            await interaction.followup.send(
                "❌ An error occurred while retrieving your demographic status. Please try again.",
                ephemeral=True
            )

    # Create admin demographic command group
    admin_demo_group = app_commands.Group(name="admin_demo", description="Admin demographic management commands")

    @admin_demo_group.command(
        name="overview",
        description="View all candidates' demographic progress and leadership"
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
            description="All presidential candidates' demographic progress and leadership",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        current_year = time_config["current_rp_date"].year if time_config else 2024
        primary_year = current_year - 1 if current_year % 2 == 0 else current_year

        # Get all primary winners
        presidential_candidates = []
        winners_data = winners_config.get("winners", [])

        if isinstance(winners_data, list):
            for winner in winners_data:
                if (isinstance(winner, dict) and
                    winner.get("primary_winner", False) and 
                    winner.get("year") == primary_year and
                    winner.get("office") in ["President", "Vice President"]):
                    presidential_candidates.append(winner)
        elif isinstance(winners_data, dict):
            # Old dict format: {party: candidate_name}
            # Get full candidate data from presidential signups
            signups_col, signups_config = self._get_presidential_config(interaction.guild.id)
            if signups_config:
                election_year = winners_config.get("election_year", current_year)
                signup_year = election_year - 1 if election_year % 2 == 0 else election_year

                for party, winner_name in winners_data.items():
                    if isinstance(winner_name, str):
                        for candidate in signups_config.get("candidates", []):
                            if (isinstance(candidate, dict) and
                                candidate.get("name", "").lower() == winner_name.lower() and
                                candidate.get("year") == signup_year and
                                candidate.get("office") == "President"):
                                presidential_candidates.append(candidate)
                                break

        if not presidential_candidates:
            await interaction.response.send_message(
                "❌ No primary winners found for the General Campaign.",
                ephemeral=True
            )
            return

        for candidate in presidential_candidates:
            candidate_demographics = candidate.get("demographic_points", {})

            # Count how many demographics they're leading
            leading_count = 0
            for demographic in DEMOGRAPHIC_STRENGTH.keys():
                leader, _ = self._get_demographic_leader(interaction.guild.id, demographic, "ALABAMA")
                if leader and leader["user_id"] == candidate["user_id"]:
                    leading_count += 1

            total_points = sum(candidate_demographics.values())
            stamina = candidate.get("stamina", 0)

            embed.add_field(
                name=f"{candidate['name']} ({candidate['party']})",
                value=f"**Leading Demographics:** {leading_count}/{len(DEMOGRAPHIC_STRENGTH)}\n"
                      f"**Total Points:** {total_points:.1f}\n"
                      f"**Stamina:** {stamina:.1f}",
                inline=True
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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

    async def candidate_autocomplete_modify(self, interaction: discord.Interaction, current: str):
        return await self.candidate_autocomplete_reset(interaction, current)

    async def demographic_autocomplete_modify(self, interaction: discord.Interaction, current: str):
        demographics = list(DEMOGRAPHIC_STRENGTH.keys())
        return [app_commands.Choice(name=demo, value=demo)
                for demo in demographics if current.lower() in demo.lower()][:25]

    @admin_demo_group.command(
        name="reset",
        description="Reset all demographic progress for a candidate"
    )
    @app_commands.describe(candidate_name="Name of the candidate to reset")
    @app_commands.autocomplete(candidate_name=candidate_autocomplete_reset)
    @app_commands.default_permissions(administrator=True)
    async def admin_demographic_reset(self, interaction: discord.Interaction, candidate_name: str):
        winners_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, candidate_name)

        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Candidate '{candidate_name}' not found.",
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

    @admin_demo_group.command(
        name="modify",
        description="Modify demographic points for a candidate"
    )
    @app_commands.describe(
        candidate_name="Name of the candidate",
        demographic="Demographic to modify",
        points="Points to set (use negative values to subtract)"
    )
    @app_commands.autocomplete(candidate_name=candidate_autocomplete_modify, demographic=demographic_autocomplete_modify)
    @app_commands.default_permissions(administrator=True)
    async def admin_demographic_modify(self, interaction: discord.Interaction, candidate_name: str, demographic: str, points: float):
        if demographic not in DEMOGRAPHIC_STRENGTH:
            await interaction.response.send_message(
                f"❌ Invalid demographic. Choose from: {', '.join(sorted(DEMOGRAPHIC_STRENGTH.keys()))}",
                ephemeral=True
            )
            return

        winners_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, candidate_name)

        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Candidate '{candidate_name}' not found.",
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

        # Check new leadership status
        leader, highest_points = self._get_demographic_leader(interaction.guild.id, demographic, "ALABAMA")
        is_now_leader = leader and leader["user_id"] == target_candidate["user_id"]

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
                  f"**Leadership:** {'🏆 Now Leading!' if is_now_leader else f'Behind leader by {max(0, highest_points - new_points):.1f}'}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_demo_group.command(
        name="clear_cooldowns",
        description="Clear all demographic cooldowns for a user"
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

    @admin_demo_group.command(
        name="reset_all",
        description="Reset ALL demographic progress for ALL candidates (DESTRUCTIVE)"
    )
    @app_commands.describe(confirm="Type 'RESET' to confirm this destructive action")
    @app_commands.default_permissions(administrator=True)
    async def admin_demographic_reset_all(self, interaction: discord.Interaction, confirm: str):
        if confirm != "RESET":
            await interaction.response.send_message(
                "⚠️ **DANGER:** This will permanently delete ALL demographic progress for ALL candidates!\n"
                "To confirm this destructive action, use: `/admin_demo_reset_all confirm:RESET`",
                ephemeral=True
            )
            return

        # Reset demographics for presidential winners
        winners_col = self.bot.db["presidential_winners"]
        winners_result = winners_col.update_many(
            {"guild_id": interaction.guild.id},
            {"$unset": {"winners.$[].demographic_points": ""}}
        )

        # Reset demographics for general signups
        signups_col = self.bot.db["signups"]
        signups_result = signups_col.update_many(
            {"guild_id": interaction.guild.id},
            {"$unset": {"candidates.$[].demographic_points": ""}}
        )

        # Clear all demographic cooldowns
        cooldowns_col = self.bot.db["demographic_cooldowns"]
        cooldowns_result = cooldowns_col.delete_many({
            "guild_id": interaction.guild.id
        })

        embed = discord.Embed(
            title="🔄 ALL Demographics Reset Complete",
            description="**ALL demographic progress has been reset for ALL candidates!**",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Reset Summary",
            value=f"**Presidential Winners:** {winners_result.modified_count} records reset\n"
                  f"**General Candidates:** {signups_result.modified_count} records reset\n"
                  f"**Cooldowns Cleared:** {cooldowns_result.deleted_count} cooldowns removed\n"
                  f"**Status:** Fresh start for all demographic campaigns",
            inline=False
        )

        embed.add_field(
            name="⚠️ Notice",
            value="All candidates now start with 0 demographic points in all categories.",
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
                if strength == 0.25:
                    strong_demos.append(demographic)
                elif strength == 0.10:
                    moderate_demos.append(demographic)
                elif strength == 0.05:
                    small_demos.append(demographic)

            if strong_demos:
                embed.add_field(
                    name="🔥 Strong Demographics (0.25x multiplier)",
                    value="\n".join(f"• {demo}" for demo in strong_demos),
                    inline=False
                )

            if moderate_demos:
                embed.add_field(
                    name="📈 Moderate Demographics (0.10x multiplier)",
                    value="\n".join(f"• {demo}" for demo in moderate_demos),
                    inline=False
                )

            if small_demos:
                embed.add_field(
                    name="📉 Small Demographics (0.05x multiplier)",
                    value="\n".join(f"• {demo}" for demo in small_demos),
                    inline=False
                )

            embed.add_field(
                name="ℹ️ How to Use",
                value="Use demographic campaigns in this state to get the listed multipliers!\n"
                      "Strong demographics give the best point gains for leadership competition.",
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
                    if strength == 0.25:  # Only show strong demographics
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
                value="Use `/view_state_demographics state_name:<STATE>` to see detailed demographics for a specific state!\n"
                      "Focus on strong demographics in key states to gain leadership!",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=False)

    @admin_demo_group.command(
        name="system_status",
        description="View demographic system configuration and statistics"
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
        config_text = f"**Total Demographics:** {len(DEMOGRAPHIC_STRENGTH)}\n"
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

        # Leadership system
        leadership_text = "**System:** Competitive Leadership\n"
        leadership_text += "**Winner:** Highest points in demographic\n"
        leadership_text += "**Benefit:** State multipliers when leading"

        embed.add_field(
            name="🏆 Leadership System",
            value=leadership_text,
            inline=True
        )

        # State multipliers
        multiplier_text = "**Small:** 0.05x multiplier\n"
        multiplier_text += "**Moderate:** 0.10x multiplier\n"
        multiplier_text += "**Strong:** 0.25x multiplier"

        embed.add_field(
            name="🗺️ State Multipliers",
            value=multiplier_text,
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @view_state_demographics.autocomplete("state_name")
    async def state_autocomplete_demographics(self, interaction: discord.Interaction, current: str):
        states = list(self.STATE_DEMOGRAPHICS.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @admin_demo_group.command(
        name="manual_demographic_set",
        description="Manually set base party percentages for a specific state"
    )
    @app_commands.describe(
        state="State to modify party percentages for",
        republican="Republican party percentage (0-100)",
        democrat="Democrat party percentage (0-100)", 
        other="Other/Independent percentage (0-100)"
    )
    @app_commands.default_permissions(administrator=True)
    async def manual_demographic_set(
        self, 
        interaction: discord.Interaction, 
        state: str, 
        republican: float, 
        democrat: float, 
        other: float
    ):
        """Manually set base party percentages for a state"""

        # Validate state
        state_upper = state.upper()
        if state_upper not in self.STATE_DEMOGRAPHICS:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(self.STATE_DEMOGRAPHICS.keys()))}",
                ephemeral=True
            )
            return

        # Validate percentages
        if not (0 <= republican <= 100 and 0 <= democrat <= 100 and 0 <= other <= 100):
            await interaction.response.send_message(
                "❌ All percentages must be between 0 and 100.",
                ephemeral=True
            )
            return

        # Calculate total for display purposes
        total = republican + democrat + other

        # Import and update presidential state data
        try:
            from .presidential_winners import PRESIDENTIAL_STATE_DATA

            # Store old values for display
            old_values = PRESIDENTIAL_STATE_DATA[state_upper].copy()

            # Update the state data
            PRESIDENTIAL_STATE_DATA[state_upper]["republican"] = round(republican, 1)
            PRESIDENTIAL_STATE_DATA[state_upper]["democrat"] = round(democrat, 1) 
            PRESIDENTIAL_STATE_DATA[state_upper]["other"] = round(other, 1)

            embed = discord.Embed(
                title="📊 Base Party Percentages Updated",
                description=f"**{state_upper}** base party percentages have been manually set.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="Previous Values",
                value=f"**Republican:** {old_values['republican']:.1f}%\n"
                      f"**Democrat:** {old_values['democrat']:.1f}%\n"
                      f"**Other:** {old_values['other']:.1f}%\n"
                      f"**Total:** {sum(old_values.values()):.1f}%",
                inline=True
            )

            embed.add_field(
                name="New Values", 
                value=f"**Republican:** {republican:.1f}%\n"
                      f"**Democrat:** {democrat:.1f}%\n"
                      f"**Other:** {other:.1f}%\n"
                      f"**Total:** {total:.1f}%",
                inline=True
            )

            embed.add_field(
                name="⚠️ Notice",
                value="Changes will affect future polling and election calculations for this state.",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except ImportError:
            await interaction.response.send_message(
                "❌ Error: Could not access presidential state data. Please check system configuration.",
                ephemeral=True
            )
            return

    @manual_demographic_set.autocomplete("state")
    async def state_autocomplete_manual_set(self, interaction: discord.Interaction, current: str):
        states = list(self.STATE_DEMOGRAPHICS.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

async def setup(bot):
    await bot.add_cog(Demographics(bot))