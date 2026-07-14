#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Excepciones personalizadas para la configuración de QC_DataMet."""


class ConfigError(Exception):
    """Excepción base para errores de configuración."""


class ConfigFileNotFoundError(ConfigError):
    """Se lanza cuando no existe un archivo de configuración obligatorio."""


class ConfigYAMLError(ConfigError):
    """Se lanza cuando un archivo YAML contiene sintaxis inválida."""


class ConfigValidationError(ConfigError):
    """Se lanza cuando la configuración no supera las validaciones."""