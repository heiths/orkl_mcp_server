# ORKL MCP Server Usage Guide

This document describes how to use the ORKL MCP Server with Claude or other MCP-compatible assistants.

## Available Tools

The ORKL MCP Server provides the following tools for interacting with the ORKL Threat Intelligence API:

### Fetch Latest Threat Reports

Retrieve the most recent threat intelligence reports from the ORKL library.

### Fetch Threat Report Details

Retrieve detailed information about a specific threat report by ID.

### Fetch Threat Report By Hash

Retrieve a specific threat report using its SHA1 hash.

### Search Threat Reports

Search the ORKL library for threat reports matching specific criteria.

### Get Library Info

Retrieve general information about the ORKL threat intelligence library.

### Get Library Version

Retrieve the latest version information for the ORKL library.

### Fetch Threat Actors

Retrieve a list of all threat actors in the ORKL database.

### Fetch Threat Actor Details

Retrieve detailed information about a specific threat actor.

### Fetch Sources

Retrieve a list of all sources in the ORKL database.

### Fetch Source Details

Retrieve detailed information about a specific source.

### Clear Cache

Clear the server's cache for more up-to-date information retrieval.

## Available Resources

The ORKL MCP Server provides the following resources for accessing ORKL data:

### Threat Report Resource

Direct access to specific threat reports via `threat_reports://{report_id}`.

### Threat Actor Resource

Direct access to specific threat actor profiles via `threat_actors://{actor_id}`.

### Source Resource

Direct access to specific source information via `sources://{source_id}`.

## Example Prompts

Here are some example prompts to use with Claude:

### Basic Threat Intelligence Search

"Can you search for recent threat reports about ransomware in the healthcare sector? Use the ORKL API to find relevant information."

### Threat Actor Analysis

"I need information about the threat actor known as 'APT29'. Can you fetch details about this actor and summarize their tactics, techniques, and procedures?"

### Source Credibility Check

"I found a report with SHA1 hash 'abc123'. Can you use the ORKL API to verify if this report comes from a credible source?"
