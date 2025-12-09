# Artisan Core Module Documentation

## File: `src/artisanlib/__init__.py`

### Overview
This is the core initialization file for the Artisan library (`artisanlib`), which serves as the foundation for the Artisan coffee roasting application. This file establishes the module's identity, versioning, and release sponsorship information.

### Purpose
The `__init__.py` file performs several critical functions:
1. **Module Declaration**: Marks the `artisanlib` directory as a Python package
2. **Version Management**: Provides version information for the entire Artisan application
3. **Release Attribution**: Credits sponsors and maintains transparency about funding sources
4. **Package Identity**: Establishes the module's public interface and metadata

### Code Analysis

#### Version Information
```python
__version__ = '3.1.5'
__revision__ = ''
__build__ = '0'
```

**`__version__`**: 
- **Type**: String
- **Value**: '3.1.5'
- **Format**: Semantic versioning (MAJOR.MINOR.PATCH)
- **Significance**: 
  - **MAJOR (3)**: Major version indicating significant architectural changes or breaking API modifications
  - **MINOR (1)**: Minor version indicating new features or enhancements
  - **PATCH (5)**: Patch version indicating bug fixes and minor improvements
- **Usage**: Used throughout the application for version checking, compatibility validation, and user interface display

**`__revision__`**: 
- **Type**: String
- **Value**: Empty string ('')
- **Purpose**: Reserved for revision control system identifiers (e.g., Git commit hashes, SVN revision numbers)
- **Current State**: Unused, likely placeholder for future implementation

**`__build__`**: 
- **Type**: String
- **Value**: '0'
- **Purpose**: Build number for continuous integration/deployment systems
- **Current State**: Set to '0', indicating either no build system integration or placeholder value

#### Release Sponsorship
```python
__release_sponsor_name__ = 'Acaia'
__release_sponsor_domain__ = 'acaia.co'
__release_sponsor_url__ = 'https://acaia.co/'
```

**Sponsorship Model**:
- **Company**: Acaia (coffee scale and measurement equipment manufacturer)
- **Domain**: acaia.co
- **URL**: https://acaia.co/

**Business Implications**:
- Indicates a commercial sponsorship or partnership arrangement
- Suggests potential integration with Acaia hardware products
- May influence feature development priorities or hardware compatibility
- Provides transparency about funding sources

### Technical Architecture

#### Module Structure
```
artisanlib/
├── __init__.py          # This file - core module definition
├── main.py              # Main application window and logic
├── canvas.py            # Roasting curve visualization
├── plugins/             # Plugin system
├── notifications.py     # User notification system
└── [other modules]      # Additional functionality
```

#### Import Behavior
When `artisanlib` is imported, this file executes and establishes:
- Package namespace
- Version constants accessible via `artisanlib.__version__`
- Sponsor information for licensing/attribution purposes

#### Version Access Patterns
```python
# Direct access
import artisanlib
version = artisanlib.__version__

# From main application
from artisanlib import main
# Version info available in main module context

# Plugin system access
# Plugins can import and check version for compatibility
```

### Integration Points

#### Application Startup
1. **Main Entry Point**: `artisan.py` imports `artisanlib.main`
2. **Version Check**: Application validates version compatibility
3. **Plugin Loading**: Plugin system checks version requirements
4. **UI Display**: Version shown in About dialog or status bar

#### Plugin System
- Plugins can access version information for compatibility checking
- Plugin manager validates version requirements
- Version-dependent features can be conditionally enabled

#### Hardware Integration
- Acaia sponsorship suggests potential hardware integration
- Version compatibility with Acaia firmware/software
- Driver compatibility matrix based on version

### Security and Licensing Considerations

#### Version Exposure
- Version information is publicly accessible
- No sensitive information in this file
- Version can be used for vulnerability assessment

#### Sponsor Attribution
- Required for license compliance
- Must be displayed in application UI
- Cannot be removed or modified without permission

### Development Workflow

#### Version Management
1. **Release Process**: Update `__version__` before each release
2. **Build Integration**: Set `__build__` from CI/CD pipeline
3. **Revision Tracking**: Populate `__revision__` from version control
4. **Testing**: Verify version propagation throughout application

#### Sponsor Updates
1. **Contract Changes**: Update sponsor information as needed
2. **Legal Review**: Ensure compliance with sponsorship agreements
3. **UI Updates**: Update application displays of sponsor information

### Future Considerations

#### Version Evolution
- **4.0.0**: Major architectural changes (breaking changes)
- **3.2.0**: New features while maintaining compatibility
- **3.1.6**: Bug fixes and minor improvements

#### Build System Integration
- Integrate with CI/CD pipelines for automatic build numbering
- Add build timestamp or environment information
- Implement version validation and testing

#### Revision Tracking
- Automate revision number population from Git
- Add build metadata (compiler, platform, dependencies)
- Implement version signing for security

### Related Files and Dependencies

#### Direct Dependencies
- **None**: This file has no imports or external dependencies

#### Dependent Modules
- **main.py**: Primary consumer of version information
- **plugins/**: Plugin system uses version for compatibility
- **UI modules**: Display version and sponsor information
- **External tools**: Build scripts, installers, documentation generators

#### Configuration Files
- **setup.py**: Uses version for package metadata
- **pyproject.toml**: Version specification for build tools
- **debian/control**: Package version for distribution

### Testing and Validation

#### Version Propagation Test
```python
def test_version_propagation():
    import artisanlib
    assert artisanlib.__version__ == '3.1.5'
    assert artisanlib.__release_sponsor_name__ == 'Acaia'
```

#### Sponsor Information Test
```python
def test_sponsor_information():
    import artisanlib
    assert artisanlib.__release_sponsor_domain__ == 'acaia.co'
    assert artisanlib.__release_sponsor_url__ == 'https://acaia.co/'
```

### Conclusion

This `__init__.py` file serves as the foundational identity document for the Artisan application. It establishes version control, maintains transparency about funding sources, and provides a clean interface for other modules to access core application metadata. The file's simplicity belies its importance in the overall application architecture and business model.

The version '3.1.5' indicates a mature, stable application with ongoing development, while the Acaia sponsorship suggests a commercial focus on professional coffee roasting equipment integration. This combination positions Artisan as a professional-grade tool with commercial backing and hardware integration capabilities.