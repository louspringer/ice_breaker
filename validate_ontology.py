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

# Get absolute path to workspace
WORKSPACE_PATH = os.path.dirname(os.path.abspath(__file__))
BASE_URI = f"file://{WORKSPACE_PATH}/"

# Define namespaces using absolute paths
ICEBREAKER = Namespace(BASE_URI + "icebreaker#")
META = Namespace(BASE_URI + "meta#")
METAMETA = Namespace(BASE_URI + "metameta#")
PROBLEM = Namespace(BASE_URI + "problem#")
SOLUTION = Namespace(BASE_URI + "solution#")
CONVERSATION = Namespace(BASE_URI + "conversation#")
MAP = Namespace(BASE_URI + "ontology_sql_mappings#")  # Note: Changed to match actual file name
BEST = Namespace(BASE_URI + "ontology_best_practices#")
EXTENSIONS = Namespace(BASE_URI + "imported_ontology_extensions#")

# Standard ontology namespaces
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
DC = Namespace("http://purl.org/dc/elements/1.1/")
SH = Namespace("http://www.w3.org/ns/shacl#")

class OntologyValidator:
    def __init__(self, ontology_file):
        """Initialize the validator with the ontology file path."""
        self.ontology_file = ontology_file
        self.graph = Graph()
        
        # Bind namespaces
        self.graph.bind('icebreaker', ICEBREAKER)
        self.graph.bind('meta', META)
        self.graph.bind('metameta', METAMETA)
        self.graph.bind('prob', PROBLEM)
        self.graph.bind('sol', SOLUTION)
        self.graph.bind('conversation', CONVERSATION)
        self.graph.bind('map', MAP)
        self.graph.bind('owl', OWL)
        self.graph.bind('rdfs', RDFS)
        self.graph.bind('rdf', RDF)
        self.graph.bind('best', BEST)
        self.graph.bind('ext', EXTENSIONS)
        
        # Bind standard namespaces
        self.graph.bind('xsd', XSD)
        self.graph.bind('dc', DC)
        self.graph.bind('sh', SH)
        
        self.load_ontology()

    def load_ontology(self):
        """Load the ontology and its imports into the graph."""
        try:
            # Load main ontology
            self.graph.parse(self.ontology_file, format="turtle")
            logger.info(f"Successfully loaded ontology from {self.ontology_file}")
            
            # Debug output for main ontology
            logger.debug("Main ontology triples:")
            for s, p, o in self.graph:
                logger.debug(f"  {s} {p} {o}")
            
            # Load imported ontologies and mappings
            import_files = {
                "meta.ttl": META,
                "metameta.ttl": METAMETA,
                "problem.ttl": PROBLEM,
                "solution.ttl": SOLUTION,
                "conversation.ttl": CONVERSATION,
                "ontology_sql_mappings.ttl": MAP,
                "imported_ontology_extensions.ttl": None
            }
            
            for file, ns in import_files.items():
                if os.path.exists(file):
                    self.graph.parse(file, format="turtle")
                    logger.info(f"Loaded imported ontology: {file}")
                    # Debug output for each import
                    logger.debug(f"Triples from {file}:")
                    if ns:
                        for s, p, o in self.graph.triples((None, None, None)):
                            if str(s).startswith(str(ns)) or str(p).startswith(str(ns)):
                                logger.debug(f"  {s} {p} {o}")
                else:
                    logger.warning(f"Import file not found: {file}")
                    
        except Exception as e:
            logger.error(f"Error loading ontology: {str(e)}")
            raise

    def validate_owl_consistency(self):
        """Validate OWL consistency checks."""
        logger.info("Validating OWL consistency...")
        
        issues = []
        
        # Core class validation
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            # Basic metadata checks
            if not any(self.graph.triples((cls, RDFS.label, None))):
                issues.append(f"Class {cls} missing rdfs:label")
            if not any(self.graph.triples((cls, RDFS.comment, None))):
                issues.append(f"Class {cls} missing rdfs:comment")
            
            # Class hierarchy checks
            superclasses = list(self.graph.objects(cls, RDFS.subClassOf))
            if not superclasses and cls != OWL.Thing:
                issues.append(f"Class {cls} not in class hierarchy")

        # Property validation
        for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
            for prop in self.graph.subjects(RDF.type, prop_type):
                # Domain/range checks
                if not any(self.graph.triples((prop, RDFS.domain, None))):
                    issues.append(f"Property {prop} missing rdfs:domain")
                if not any(self.graph.triples((prop, RDFS.range, None))):
                    issues.append(f"Property {prop} missing rdfs:range")
                
                # Metadata checks
                if not any(self.graph.triples((prop, RDFS.label, None))):
                    issues.append(f"Property {prop} missing rdfs:label")

        # Temporal tracking validation
        temporal_classes = [
            ICEBREAKER.TemporalTracking,
            ICEBREAKER.VersionChain,
            ICEBREAKER.ChangeContext
        ]
        for cls in temporal_classes:
            if not any(self.graph.triples((None, RDFS.subClassOf, cls))):
                issues.append(f"Temporal tracking class {cls} has no subclasses")

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
            pairs = {}
            for s, o in self.graph.subject_objects(prop):
                if s in pairs:
                    issues.append(f"Functional property {prop} has multiple values for subject {s}")
                pairs[s] = o

        # Check cardinality restrictions
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            for restriction in self.graph.objects(cls, RDFS.subClassOf):
                if (restriction, RDF.type, OWL.Restriction) in self.graph:
                    prop = self.graph.value(restriction, OWL.onProperty)
                    card = self.graph.value(restriction, OWL.cardinality)
                    if card and int(card) != 1:
                        issues.append(f"Invalid cardinality {card} for property {prop} on class {cls}")

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

        # Validate temporal tracking completeness
        temporal_entities = list(self.graph.subjects(RDF.type, ICEBREAKER.TemporalTracking))
        for entity in temporal_entities:
            if not any(self.graph.triples((entity, ICEBREAKER.changeTimestamp, None))):
                issues.append(f"Temporal entity {entity} missing changeTimestamp")
            if not any(self.graph.triples((entity, ICEBREAKER.changeType, None))):
                issues.append(f"Temporal entity {entity} missing changeType")

        # Validate data quality metrics
        quality_records = list(self.graph.subjects(RDF.type, ICEBREAKER.DataQuality))
        for record in quality_records:
            if not any(self.graph.triples((record, ICEBREAKER.confidenceScore, None))):
                issues.append(f"Quality record {record} missing confidenceScore")
            if not any(self.graph.triples((record, ICEBREAKER.lastVerifiedDate, None))):
                issues.append(f"Quality record {record} missing lastVerifiedDate")

        # Validate integration metadata
        integration_records = list(self.graph.subjects(RDF.type, ICEBREAKER.IntegrationMetadata))
        for record in integration_records:
            if not any(self.graph.triples((record, ICEBREAKER.syncStatus, None))):
                issues.append(f"Integration record {record} missing syncStatus")

        return issues

    def _find_property_by_name(self, prop_uri):
        """Helper method to find a property by name across all namespaces."""
        # Try direct match first
        if any(self.graph.triples((prop_uri, RDF.type, None))):
            return prop_uri
            
        # Try searching by local name
        local_name = str(prop_uri).split('#')[-1]
        
        # Search across all properties
        for s, p, o in self.graph.triples((None, RDF.type, None)):
            if o in [OWL.ObjectProperty, OWL.DatatypeProperty, RDF.Property]:
                if str(s).split('#')[-1] == local_name:
                    return s
                    
        # Check core RDF/RDFS/OWL properties
        core_properties = {
            'label': RDFS.label,
            'comment': RDFS.comment,
            'type': RDF.type,
            'subClassOf': RDFS.subClassOf,
            'subPropertyOf': RDFS.subPropertyOf,
            'domain': RDFS.domain,
            'range': RDFS.range
        }
        
        if local_name in core_properties:
            return core_properties[local_name]
            
        return None

    def validate_sql_mappings(self):
        """Validate SQL mappings between ontology and database schema."""
        logger.info("Validating SQL mappings...")
        issues = []

        # Get all column mappings
        column_mappings = list(self.graph.subjects(RDF.type, MAP.ColumnMapping))
        
        for mapping in column_mappings:
            # Get the mapped property
            mapped_props = list(self.graph.objects(mapping, MAP.mapsProperty))
            
            if not mapped_props:
                continue  # Skip if no property mapping
                
            mapped_prop = mapped_props[0]
            
            # Try to find the actual property
            actual_prop = self._find_property_by_name(mapped_prop)
            
            if not actual_prop:
                # Get mapping name for better error message
                mapping_name = str(mapping).split('#')[-1]
                prop_name = str(mapped_prop).split('#')[-1]
                issues.append(f"Column mapping {mapping_name} references non-existent property {prop_name}")
                continue
                
            # Validate property type compatibility
            prop_types = self._get_property_type(actual_prop)
            if not (OWL.DatatypeProperty in prop_types or OWL.ObjectProperty in prop_types or RDF.Property in prop_types):
                mapping_name = str(mapping).split('#')[-1]
                prop_name = str(mapped_prop).split('#')[-1]
                issues.append(f"Column mapping {mapping_name} references invalid property type for {prop_name}")
                
            # Validate SQL data type compatibility
            if OWL.DatatypeProperty in prop_types:
                sql_type = self.graph.value(mapping, MAP.hasDataType)
                if not sql_type:
                    mapping_name = str(mapping).split('#')[-1]
                    issues.append(f"Column mapping {mapping_name} missing SQL data type for datatype property")

        return issues

    def validate_class_hierarchy(self):
        """Validate the class hierarchy completeness and consistency."""
        logger.info("Validating class hierarchy...")
        issues = []
        
        # Get all classes
        classes = set()
        for s, p, o in self.graph.triples((None, RDF.type, OWL.Class)):
            classes.add(s)
            
        # Skip validation for auto-generated IDs (they start with 'n' followed by hex)
        def is_auto_generated(class_uri):
            class_name = str(class_uri).split('#')[-1]
            return class_name.startswith('n') and len(class_name) > 30 and all(c in '0123456789abcdef' for c in class_name[1:])
            
        for class_uri in classes:
            if is_auto_generated(class_uri):
                continue
                
            # Check for label
            labels = list(self.graph.objects(class_uri, RDFS.label))
            if not labels:
                class_name = str(class_uri).split('#')[-1]
                issues.append(f"Class {class_name} missing rdfs:label")
            
            # Check for comment
            comments = list(self.graph.objects(class_uri, RDFS.comment))
            if not comments:
                class_name = str(class_uri).split('#')[-1]
                issues.append(f"Class {class_name} missing rdfs:comment")
            
            # Check class is in hierarchy (has parent or children)
            has_parent = any(self.graph.triples((class_uri, RDFS.subClassOf, None)))
            has_children = any(self.graph.triples((None, RDFS.subClassOf, class_uri)))
            
            if not has_parent and not has_children and class_uri != OWL.Thing:
                class_name = str(class_uri).split('#')[-1]
                issues.append(f"Class {class_name} not in class hierarchy")
        
        return issues

    def _get_property_type(self, prop_uri):
        """Helper method to determine property type including inheritance."""
        # Direct type check
        types = set()
        for _, _, t in self.graph.triples((prop_uri, RDF.type, None)):
            types.add(t)
            
        # Check super-properties
        for parent in self.graph.objects(prop_uri, RDFS.subPropertyOf):
            parent_types = self._get_property_type(parent)
            types.update(parent_types)
            
        return types

    def _is_valid_property_type(self, found_types, expected_type):
        """Check if the found types are compatible with expected type."""
        if expected_type in found_types:
            return True
            
        # Handle property inheritance
        if OWL.ObjectProperty == expected_type:
            return any(t for t in found_types if t in [
                OWL.ObjectProperty,
                OWL.FunctionalProperty,
                OWL.InverseFunctionalProperty,
                OWL.SymmetricProperty,
                OWL.TransitiveProperty
            ])
        elif OWL.DatatypeProperty == expected_type:
            return any(t for t in found_types if t in [
                OWL.DatatypeProperty,
                OWL.FunctionalProperty
            ])
            
        return False

    def validate_property_metadata(self):
        """Validate property metadata completeness with improved type checking."""
        logger.info("Validating property metadata...")
        
        issues = []
        
        # Required property URIs with their expected types
        required_properties = [
            (META.hasLevel, "meta:hasLevel", OWL.DatatypeProperty),
            (PROBLEM.hasContext, "prob:hasContext", OWL.ObjectProperty),
            (PROBLEM.hasConstraint, "prob:hasConstraint", OWL.ObjectProperty),
            (SOLUTION.satisfies, "sol:satisfies", OWL.ObjectProperty),
            (SOLUTION.hasImplementation, "sol:hasImplementation", OWL.ObjectProperty),
            (SOLUTION.hasValidation, "sol:hasValidation", OWL.ObjectProperty),
            (METAMETA.levelNumber, "metameta:levelNumber", OWL.DatatypeProperty),
            (METAMETA.domainScope, "metameta:domainScope", OWL.DatatypeProperty),
            (PROBLEM.hasValue, "prob:hasValue", OWL.DatatypeProperty),
            (PROBLEM.hasPriority, "prob:hasPriority", OWL.DatatypeProperty),
            (SOLUTION.validationStatus, "sol:validationStatus", OWL.DatatypeProperty),
            (MAP.hasTableName, "map:hasTableName", OWL.DatatypeProperty),
            (MAP.hasColumnName, "map:hasColumnName", OWL.DatatypeProperty),
            (MAP.hasDataType, "map:hasDataType", OWL.DatatypeProperty)
        ]
        
        # Debug total triples and namespaces
        logger.debug(f"Total triples in graph: {len(self.graph)}")
        logger.debug("Namespaces bound:")
        for prefix, ns in self.graph.namespaces():
            logger.debug(f"  {prefix}: {ns}")
        
        for prop_uri, prop_name, expected_type in required_properties:
            # Debug property checking
            logger.debug(f"\nChecking property {prop_name} ({prop_uri})")
            
            # Try to find the property with both relative and absolute URIs
            prop_triples = list(self.graph.triples((prop_uri, None, None)))
            
            if not prop_triples:
                # Try searching by local name
                local_name = str(prop_uri).split('#')[-1]
                found = False
                for s, p, o in self.graph.triples((None, RDF.type, None)):
                    if str(s).split('#')[-1] == local_name:
                        prop_uri = s
                        prop_triples = list(self.graph.triples((s, None, None)))
                        found = True
                        break
                
                if not found:
                    issues.append(f"Property {prop_name} not found in ontology")
                    continue
            
            # Get all property types including inherited ones
            found_types = self._get_property_type(prop_uri)
            logger.debug(f"Property types found: {found_types}")
            
            # Check if property type is valid
            if not self._is_valid_property_type(found_types, expected_type):
                issues.append(f"Property {prop_name} has incompatible type. Expected {expected_type}, found {found_types}")
                continue
            
            # Check for label
            labels = list(self.graph.objects(prop_uri, RDFS.label))
            if not labels:
                issues.append(f"Missing label for property: {prop_name}")
            else:
                logger.debug(f"Found labels: {labels}")

        return issues

    def validate_best_practices(self):
        """Validate against best practices defined in ontology_best_practices.ttl."""
        logger.info("Validating against best practices...")
        
        issues = []
        
        try:
            # Load best practices ontology
            best_practices_graph = Graph()
            best_practices_graph.parse("ontology_best_practices.ttl", format="turtle")
            
            # Get all validation rules
            validation_rules = list(best_practices_graph.subjects(RDF.type, BEST.ValidationRule))
            
            for rule in validation_rules:
                priority = best_practices_graph.value(rule, BEST.priority)
                rule_label = best_practices_graph.value(rule, RDFS.label)
                
                logger.debug(f"Checking rule: {rule_label} (Priority: {priority})")
                
                # Property Label Rule
                if rule == BEST.PropertyLabelRule:
                    for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
                        if not any(self.graph.triples((prop, RDFS.label, None))):
                            issues.append(f"Property {prop} missing rdfs:label (Priority 1)")
                            
                    for prop in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
                        if not any(self.graph.triples((prop, RDFS.label, None))):
                            issues.append(f"Property {prop} missing rdfs:label (Priority 1)")
                
                # Property Type Rule
                elif rule == BEST.PropertyTypeRule:
                    for prop in self.graph.subjects(None, RDF.type):
                        if any(self.graph.triples((prop, RDF.type, RDF.Property))):
                            if not any(self.graph.triples((prop, RDF.type, OWL.ObjectProperty))) and \
                               not any(self.graph.triples((prop, RDF.type, OWL.DatatypeProperty))):
                                issues.append(f"Property {prop} missing explicit type declaration (Priority 1)")
                
                # Domain Range Rule
                elif rule == BEST.DomainRangeRule:
                    for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
                        if not any(self.graph.triples((prop, RDFS.domain, None))):
                            issues.append(f"Object property {prop} missing rdfs:domain (Priority 2)")
                        if not any(self.graph.triples((prop, RDFS.range, None))):
                            issues.append(f"Object property {prop} missing rdfs:range (Priority 2)")
                    
                    for prop in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
                        if not any(self.graph.triples((prop, RDFS.domain, None))):
                            issues.append(f"Datatype property {prop} missing rdfs:domain (Priority 2)")
                        if not any(self.graph.triples((prop, RDFS.range, None))):
                            issues.append(f"Datatype property {prop} missing rdfs:range (Priority 2)")
                
                # Namespace Consistency Rule
                elif rule == BEST.NamespaceConsistencyRule:
                    # Get all namespaces used in URIs
                    used_namespaces = set()
                    standard_namespaces = {
                        str(XSD): 'xsd',
                        str(DC): 'dc',
                        str(OWL): 'owl',
                        str(RDF): 'rdf',
                        str(RDFS): 'rdfs',
                        str(SH): 'sh'
                    }
                    
                    for s, p, o in self.graph:
                        for uri in (s, p, o):
                            if isinstance(uri, URIRef):
                                ns = str(uri).split('#')[0] + '#'
                                if ns not in standard_namespaces:
                                    used_namespaces.add(ns)
                    
                    # Check if all used namespaces are properly bound
                    bound_namespaces = {str(ns) for prefix, ns in self.graph.namespaces()}
                    
                    for ns in used_namespaces:
                        if ns not in bound_namespaces and \
                           not any(ns.startswith(str(std_ns)) for std_ns in standard_namespaces):
                            # Convert absolute file paths to relative for clearer messages
                            if ns.startswith('file://'):
                                relative_ns = ns.split(WORKSPACE_PATH)[1].lstrip('/')
                                issues.append(f"Local namespace '{relative_ns}' is used but not properly bound (Priority 1)")
                            else:
                                issues.append(f"Namespace '{ns}' is used but not properly bound (Priority 1)")
            
            return issues
            
        except Exception as e:
            logger.error(f"Error during best practices validation: {str(e)}")
            raise

    def run_all_validations(self):
        """Run all validation checks and return comprehensive results."""
        validation_results = {
            'owl_consistency': self.validate_owl_consistency(),
            'shacl_constraints': self.validate_shacl_constraints(),
            'cardinality_constraints': self.validate_cardinality_constraints(),
            'custom_rules': self.validate_custom_rules(),
            'sql_mappings': self.validate_sql_mappings(),
            'class_hierarchy': self.validate_class_hierarchy(),
            'property_metadata': self.validate_property_metadata(),
            'best_practices': self.validate_best_practices()
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
        
        validation_sections = [
            ('owl_consistency', "OWL Consistency"),
            ('shacl_constraints', "SHACL Constraints"),
            ('cardinality_constraints', "Cardinality Constraints"),
            ('custom_rules', "Custom Rules"),
            ('sql_mappings', "SQL Mappings"),
            ('class_hierarchy', "Class Hierarchy"),
            ('property_metadata', "Property Metadata"),
            ('best_practices', "Best Practices")
        ]
        
        for key, title in validation_sections:
            result = results[key]
            if key == 'shacl_constraints':
                conforms, results_text = result
                if conforms:
                    logger.info(f"{title}: OK")
                else:
                    logger.warning(f"{title} Issues:")
                    logger.warning(results_text)
            elif result:
                logger.warning(f"{title} Issues:")
                for issue in result:
                    logger.warning(f"- {issue}")
            else:
                logger.info(f"{title}: OK")
            
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 