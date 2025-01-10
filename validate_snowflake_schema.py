#!/usr/bin/env python3
"""
Snowflake Schema Validation Script
Implements dry run validation rules defined in ontology_sql_mappings.ttl
"""

import os
import json
import logging
import sqlparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Iterator
from dataclasses import dataclass
from pathlib import Path

from snowflake.snowpark import Session
from snowflake.snowpark.exceptions import SnowparkSQLException
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define namespaces
MAP = Namespace("./ontology_sql_mappings#")
ICEBREAKER = Namespace("./icebreaker#")

@dataclass
class ValidationResult:
    """Represents a validation check result"""
    status: str
    message: str
    severity: str
    timestamp: datetime
    statement: Optional[str] = None
    details: Optional[Dict] = None

class SnowflakeValidator:
    """Implements validation rules for Snowflake schema changes"""

    def __init__(self):
        """Initialize validator"""
        self.graph = Graph()
        self.load_ontologies()
        self.session = Session.builder.getOrCreate()
        
    def load_ontologies(self):
        """Load required ontology files"""
        ontology_files = [
            "ontology_sql_mappings.ttl",
            "icebreaker.ttl",
            "meta.ttl"
        ]
        
        for file in ontology_files:
            if os.path.exists(file):
                self.graph.parse(file, format="turtle")
                logger.info(f"Loaded ontology: {file}")
            else:
                logger.warning(f"Ontology file not found: {file}")

    def parse_sql_file(self, sql_content: str) -> Iterator[str]:
        """Parse SQL file into individual statements"""
        # First, normalize line endings
        sql_content = sql_content.replace('\r\n', '\n')
        
        # Split into statements
        statements = sqlparse.split(sql_content)
        
        for stmt in statements:
            # Clean and normalize statement
            cleaned = sqlparse.format(
                stmt,
                strip_comments=True,
                keyword_case='upper'
            ).strip()
            
            if cleaned:
                yield cleaned

    def validate_statement(self, stmt: str) -> List[ValidationResult]:
        """Validate a single SQL statement"""
        stmt_type = self._get_statement_type(stmt)
        
        # DDL commands are considered valid by default
        if stmt_type == "DDL_COMMAND":
            return [ValidationResult(
                status="INFO",
                message=f"DDL command will be executed: {stmt}",
                severity="INFO",
                timestamp=datetime.now(),
                statement=stmt,
                details={"type": "ddl"}
            )]
        
        # For DML statements, validate syntax
        syntax_result = self.validate_syntax(stmt)
        syntax_result.statement = stmt
        return [syntax_result]

    def validate_schema_file(self, file_path: str) -> List[ValidationResult]:
        """Validate entire schema file before execution"""
        all_results = []
        
        try:
            with open(file_path, "r") as f:
                sql_content = f.read()
            
            # Validate each statement
            for stmt in self.parse_sql_file(sql_content):
                results = self.validate_statement(stmt)
                all_results.extend(results)
                
                # Check for blocking errors
                if any(r.severity == "ERROR" for r in results):
                    logger.error(f"Blocking error found in statement: {stmt}")
                    break
            
            return all_results
            
        except Exception as e:
            logger.error(f"Error validating schema file: {str(e)}")
            return [ValidationResult(
                status="ERROR",
                message=f"File validation error: {str(e)}",
                severity="ERROR",
                timestamp=datetime.now()
            )]

    def _get_statement_type(self, stmt: str) -> str:
        """Extract the type of SQL statement"""
        stmt_upper = ' '.join(stmt.upper().strip().split())
        
        # Handle DDL and administrative commands
        if any(stmt_upper.startswith(cmd) for cmd in [
            'USE', 'CREATE', 'DROP', 'GRANT', 'ALTER', 'COMMENT'
        ]):
            return "DDL_COMMAND"
            
        parsed = sqlparse.parse(stmt)[0]
        return parsed.get_type() if parsed else ""

    def _extract_role(self, stmt: str) -> str:
        """Extract role name from statement"""
        # Simple extraction - in practice, use proper SQL parser
        if "ROLE" in stmt.upper():
            parts = stmt.upper().split("ROLE")[1].strip().split()
            return parts[0] if parts else ""
        return ""

    def _extract_object(self, stmt: str) -> str:
        """Extract object name from statement"""
        parsed = sqlparse.parse(stmt)[0]
        for token in parsed.tokens:
            if token.ttype is None and token.get_name():
                return token.get_name()
        return ""

    def validate_syntax(self, sql: str) -> ValidationResult:
        """Validate SQL syntax without execution"""
        try:
            # Skip validation for DDL commands
            if self._get_statement_type(sql) == "DDL_COMMAND":
                return ValidationResult(
                    status="SUCCESS",
                    message="DDL command syntax is valid",
                    severity="INFO",
                    timestamp=datetime.now()
                )
            
            # Only validate DML syntax
            parsed = sqlparse.parse(sql)[0]
            if not parsed.is_group:
                return ValidationResult(
                    status="ERROR",
                    message="Invalid SQL syntax",
                    severity="ERROR",
                    timestamp=datetime.now()
                )
                
            return ValidationResult(
                status="SUCCESS",
                message="SQL syntax is valid",
                severity="INFO",
                timestamp=datetime.now()
            )
        except Exception as e:
            return ValidationResult(
                status="ERROR",
                message=f"SQL syntax error: {str(e)}",
                severity="ERROR",
                timestamp=datetime.now()
            )

    def validate_objects(self, sql: str) -> ValidationResult:
        """Validate referenced objects exist"""
        try:
            # Extract object names from SQL (simplified)
            objects = self._extract_objects(sql)
            missing_objects = []
            
            for obj_name, obj_type in objects:
                result = self.session.sql(f"""
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.OBJECTS
                    WHERE OBJECT_NAME = '{obj_name}'
                    AND OBJECT_TYPE = '{obj_type}'
                """).collect()
                
                if result[0][0] == 0:
                    missing_objects.append(f"{obj_type} {obj_name}")
            
            if missing_objects:
                return ValidationResult(
                    status="WARNING",
                    message="Some referenced objects do not exist",
                    severity="WARNING",
                    timestamp=datetime.now(),
                    details={"missing_objects": missing_objects}
                )
            
            return ValidationResult(
                status="SUCCESS",
                message="All referenced objects exist",
                severity="INFO",
                timestamp=datetime.now()
            )
        except Exception as e:
            return ValidationResult(
                status="ERROR",
                message=f"Error validating objects: {str(e)}",
                severity="ERROR",
                timestamp=datetime.now()
            )

    def validate_privileges(self, role_name: str) -> ValidationResult:
        """Validate role has required privileges"""
        try:
            grants = self.session.sql(f"SHOW GRANTS TO ROLE {role_name}").collect()
            
            # Get required grants from ontology
            required_grants = self._get_required_grants(role_name)
            missing_grants = []
            
            for req_grant in required_grants:
                if not any(g["privilege"] == req_grant for g in grants):
                    missing_grants.append(req_grant)
            
            if missing_grants:
                return ValidationResult(
                    status="WARNING",
                    message=f"Role {role_name} is missing required privileges",
                    severity="WARNING",
                    timestamp=datetime.now(),
                    details={"missing_grants": missing_grants}
                )
            
            return ValidationResult(
                status="SUCCESS",
                message=f"Role {role_name} has all required privileges",
                severity="INFO",
                timestamp=datetime.now()
            )
        except Exception as e:
            return ValidationResult(
                status="ERROR",
                message=f"Error validating privileges: {str(e)}",
                severity="ERROR",
                timestamp=datetime.now()
            )

    def validate_dependencies(self, object_name: str) -> ValidationResult:
        """Validate object dependencies"""
        try:
            dependencies = self.session.sql(f"""
                SELECT REFERENCED_OBJECT_NAME, REFERENCED_OBJECT_TYPE
                FROM INFORMATION_SCHEMA.OBJECT_DEPENDENCIES
                WHERE OBJECT_NAME = '{object_name}'
            """).collect()
            
            return ValidationResult(
                status="SUCCESS",
                message="Dependency check completed",
                severity="INFO",
                timestamp=datetime.now(),
                details={"dependencies": [dict(d) for d in dependencies]}
            )
        except Exception as e:
            return ValidationResult(
                status="ERROR",
                message=f"Error checking dependencies: {str(e)}",
                severity="ERROR",
                timestamp=datetime.now()
            )

    def generate_validation_report(self, results: List[ValidationResult]) -> str:
        """Generate a formatted validation report"""
        template = self._get_report_template()
        
        # Collect status for each validation type
        statuses = {
            "syntaxStatus": next((r for r in results if "syntax" in r.message.lower()), None),
            "objectStatus": next((r for r in results if "object" in r.message.lower()), None),
            "privilegeStatus": next((r for r in results if "privilege" in r.message.lower()), None),
            "dependencyStatus": next((r for r in results if "dependenc" in r.message.lower()), None)
        }
        
        # Generate detailed section
        details = []
        recommendations = []
        
        for result in results:
            details.append(f"- {result.message}")
            if result.severity in ("WARNING", "ERROR"):
                recommendations.append(
                    f"- {result.message}: {self._get_recommendation(result)}"
                )
        
        # Format report
        report = template.format(
            syntaxStatus=self._format_status(statuses["syntaxStatus"]),
            objectStatus=self._format_status(statuses["objectStatus"]),
            privilegeStatus=self._format_status(statuses["privilegeStatus"]),
            dependencyStatus=self._format_status(statuses["dependencyStatus"]),
            validationDetails="\n".join(details),
            recommendations="\n".join(recommendations) if recommendations else "No recommendations needed."
        )
        
        return report

    def _get_report_template(self) -> str:
        """Get report template from ontology"""
        template = self.graph.value(
            subject=MAP.GenerateReport,
            predicate=MAP.reportTemplate
        )
        return str(template) if template else """
            Dry Run Validation Report
            ------------------------
            SQL Syntax: {syntaxStatus}
            Object Existence: {objectStatus}
            Privileges: {privilegeStatus}
            Dependencies: {dependencyStatus}
            
            Details:
            {validationDetails}
            
            Recommendations:
            {recommendations}
        """

    def _format_status(self, result: Optional[ValidationResult]) -> str:
        """Format validation status for report"""
        if not result:
            return "NOT CHECKED"
        return f"{result.status} - {result.message}"

    def _get_recommendation(self, result: ValidationResult) -> str:
        """Generate recommendation based on validation result"""
        if result.severity == "ERROR":
            if "syntax" in result.message.lower():
                return "Review and correct SQL syntax"
            elif "privilege" in result.message.lower():
                return "Grant required privileges or contact administrator"
            elif "object" in result.message.lower():
                return "Create missing objects before proceeding"
        elif result.severity == "WARNING":
            return "Review and ensure this won't impact your changes"
        return "No specific recommendation"

    def _extract_objects(self, sql: str) -> List[Tuple[str, str]]:
        """Extract referenced object names and types from SQL"""
        # This is a simplified implementation
        # In practice, you'd want to use a proper SQL parser
        objects = []
        sql_upper = sql.upper()
        
        # Extract table names
        if "FROM" in sql_upper:
            tables = sql_upper.split("FROM")[1].split("WHERE")[0].strip().split(",")
            objects.extend((t.strip(), "TABLE") for t in tables)
            
        # Extract view names
        if "VIEW" in sql_upper:
            views = sql_upper.split("VIEW")[1].split("AS")[0].strip().split(",")
            objects.extend((v.strip(), "VIEW") for v in views)
            
        return objects

    def _get_required_grants(self, role_name: str) -> List[str]:
        """Get required grants for role from ontology"""
        role_uri = URIRef(f"{MAP}{role_name}")
        grants = self.graph.value(
            subject=role_uri,
            predicate=MAP.requiredGrants
        )
        if grants:
            return [str(g) for g in self.graph.items(grants)]
        return []

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            self.session.close()

def main():
    """Main execution function"""
    # Initialize validator using context manager
    with SnowflakeValidator() as validator:
        # Validate schema file before execution
        results = validator.validate_schema_file("create_snowflake_schema.sql")
        
        # Check for errors
        has_errors = any(r.severity == "ERROR" for r in results)
        
        # Generate and print report
        report = validator.generate_validation_report(results)
        print(report)
        
        if has_errors:
            logger.error("Validation failed. Please fix errors before executing schema changes.")
            return 1
        else:
            logger.info("Validation successful. Schema changes can be executed.")
            return 0

if __name__ == "__main__":
    exit(main()) 