#!/usr/bin/env python3
"""
Ontology Validation Script for Icebreaker Ontology
This script validates both OWL consistency and SHACL constraints.
"""

import os
from rdflib import Graph, Namespace, URIRef, OWL, RDFS, RDF
from pyshacl import validate
import logging

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define namespaces to match the .ttl files
ICEBREAKER = Namespace("./icebreaker#")
META = Namespace("./meta#")
METAMETA = Namespace("./metameta#")
PROBLEM = Namespace("./problem#")
SOLUTION = Namespace("./solution#")
CONVERSATION = Namespace("./conversation#")

class OntologyValidator:
    def __init__(self, ontology_file):
        """Initialize the validator with the ontology file path."""
        self.ontology_file = ontology_file
        self.graph = Graph()
        self.load_ontology()

    def load_ontology(self):
        """Load the ontology and its imports into the graph."""
        try:
            self.graph.parse(self.ontology_file, format="turtle")
            logger.info(f"Successfully loaded ontology from {self.ontology_file}")
            
            # Load imported ontologies
            import_files = {
                "meta.ttl": META,
                "metameta.ttl": METAMETA,
                "problem.ttl": PROBLEM,
                "solution.ttl": SOLUTION,
                "conversation.ttl": CONVERSATION
            }
            
            for file, ns in import_files.items():
                if os.path.exists(file):
                    self.graph.parse(file, format="turtle")
                    logger.info(f"Loaded imported ontology: {file}")
                else:
                    logger.warning(f"Import file not found: {file}")
                    
        except Exception as e:
            logger.error(f"Error loading ontology: {str(e)}")
            raise

    def validate_owl_consistency(self):
        """Validate OWL consistency checks."""
        logger.info("Validating OWL consistency...")
        
        # Check class hierarchy
        issues = []
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            # Check if class has label
            if not any(self.graph.triples((cls, RDFS.label, None))):
                issues.append(f"Class {cls} missing rdfs:label")
            
            # Check if class has comment
            if not any(self.graph.triples((cls, RDFS.comment, None))):
                issues.append(f"Class {cls} missing rdfs:comment")
            
            # Check subclass relationships
            superclasses = list(self.graph.objects(cls, RDFS.subClassOf))
            if not superclasses and cls != OWL.Thing:
                issues.append(f"Class {cls} not in class hierarchy")

        # Check property definitions
        for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            # Check if property has domain
            if not any(self.graph.triples((prop, RDFS.domain, None))):
                issues.append(f"Object property {prop} missing rdfs:domain")
            
            # Check if property has range
            if not any(self.graph.triples((prop, RDFS.range, None))):
                issues.append(f"Object property {prop} missing rdfs:range")

        return issues

    def validate_shacl_constraints(self):
        """Validate SHACL constraints."""
        logger.info("Validating SHACL constraints...")
        
        try:
            conforms, results_graph, results_text = validate(
                self.graph,
                shacl_graph=self.graph,
                inference='rdfs',
                abort_on_first=False,
                allow_infos=True,
                allow_warnings=True
            )
            
            return conforms, results_text
        except Exception as e:
            logger.error(f"Error during SHACL validation: {str(e)}")
            raise

    def validate_cardinality_constraints(self):
        """Validate cardinality constraints."""
        logger.info("Validating cardinality constraints...")
        
        issues = []
        
        # Check functional properties
        functional_props = list(self.graph.subjects(RDF.type, OWL.FunctionalProperty))
        for prop in functional_props:
            # Get all subject-object pairs for this property
            pairs = {}
            for s, o in self.graph.subject_objects(prop):
                if s in pairs:
                    issues.append(f"Functional property {prop} has multiple values for subject {s}")
                pairs[s] = o

        return issues

    def validate_custom_rules(self):
        """Validate custom business rules specific to the icebreaker ontology."""
        logger.info("Validating custom business rules...")
        
        issues = []
        
        # Validate NetworkingDegree priorities
        degrees = list(self.graph.subjects(RDF.type, ICEBREAKER.NetworkingDegree))
        for degree in degrees:
            priority = self.graph.value(degree, META.priority)
            if not priority:
                issues.append(f"NetworkingDegree {degree} missing priority value")
        
        # Validate Contact email format
        contacts = list(self.graph.subjects(RDF.type, ICEBREAKER.Contact))
        for contact in contacts:
            email = self.graph.value(contact, ICEBREAKER.contactEmail)
            if email and not '@' in str(email):
                issues.append(f"Contact {contact} has invalid email format")

        return issues

    def run_all_validations(self):
        """Run all validation checks and return comprehensive results."""
        validation_results = {
            'owl_consistency': self.validate_owl_consistency(),
            'shacl_constraints': self.validate_shacl_constraints(),
            'cardinality_constraints': self.validate_cardinality_constraints(),
            'custom_rules': self.validate_custom_rules()
        }
        
        return validation_results

def main():
    """Main function to run the validation."""
    try:
        # Initialize validator
        validator = OntologyValidator("icebreaker.ttl")
        
        # Run all validations
        results = validator.run_all_validations()
        
        # Process and display results
        logger.info("\n=== Validation Results ===")
        
        # OWL Consistency
        if results['owl_consistency']:
            logger.warning("OWL Consistency Issues:")
            for issue in results['owl_consistency']:
                logger.warning(f"- {issue}")
        else:
            logger.info("OWL Consistency: OK")
            
        # SHACL Constraints
        conforms, results_text = results['shacl_constraints']
        if conforms:
            logger.info("SHACL Constraints: OK")
        else:
            logger.warning("SHACL Validation Issues:")
            logger.warning(results_text)
            
        # Cardinality Constraints
        if results['cardinality_constraints']:
            logger.warning("Cardinality Constraint Issues:")
            for issue in results['cardinality_constraints']:
                logger.warning(f"- {issue}")
        else:
            logger.info("Cardinality Constraints: OK")
            
        # Custom Rules
        if results['custom_rules']:
            logger.warning("Custom Rule Issues:")
            for issue in results['custom_rules']:
                logger.warning(f"- {issue}")
        else:
            logger.info("Custom Rules: OK")
            
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 