# Contains lists of all errors and exceptions
# Imported in classify_bugs
# TODO: Add more bugs to *_nonstd after verification (from those detected as userdefined)

java_errors = ['AssertionError', 'LinkageError', 'BootstrapMethodError', 'ClassCircularityError', 'ClassFormatError',
               'UnsupportedClassVersionError', 'ExceptionInInitializerError', 'IncompatibleClassChangeError',
               'AbstractMethodError', 'IllegalAccessError', 'InstantiationError', 'NoSuchFieldError',
               'NoSuchMethodError', 'NoClassDefFoundError', 'UnsatisfiedLinkError', 'VerifyError', 'ThreadDeath',
               'VirtualMachineError', 'InternalError', 'OutOfMemoryError', 'StackOverflowError', 'UnknownError',
               'Error'
               ]
java_exceptions = ['ArithmeticException', 'ArrayStoreException', 'ClassCastException',
                   'EnumConstantNotPresentException', 'IllegalArgumentException', 'IllegalThreadStateException',
                   'NumberFormatException', 'IllegalMonitorStateException', 'IllegalStateException',
                   'IndexOutOfBoundsException', 'ArrayIndexOutOfBoundsException', 'StringIndexOutOfBoundsException',
                   'NegativeArraySizeException', 'NullPointerException', 'SecurityException', 'TypeNotPresentException',
                   'UnsupportedOperationException', 'Exception'
                   ]
java_all = ['AclNotFoundException', 'SyncFailedException', 'SAXNotRecognizedException', 'NameAlreadyBoundException',
            'UnsupportedClassVersionError', 'TimeoutException', 'AsynchronousCloseException',
            'ReadOnlyFileSystemException', 'InvalidKeySpecException', 'IndirectionException', 'ClassCircularityError',
            'CRLException', 'SQLClientInfoException', 'VerifyError', 'UnknownHostException',
            'ClosedByInterruptException', 'AuthenticationException', 'TypeConstraintException',
            'NonReadableChannelException', 'IllformedLocaleException', 'ObjectStreamException', 'RuntimeMBeanException',
            'CredentialExpiredException', 'ListenerNotFoundException', 'SocketException', 'IllegalClassFormatException',
            'JMException', 'IllegalThreadStateException', 'SSLHandshakeException', 'InternalError',
            'EmptyStackException', 'LambdaConversionException', 'HTTPException', 'WrongMethodTypeException',
            'ArrayStoreException', 'InvalidNameException', 'InvalidSearchFilterException', 'LoginException',
            'ValidationException', 'IllegalFormatConversionException', 'InvalidPropertiesFormatException',
            'SignatureException', 'IncompatibleClassChangeError', 'SQLRecoverableException', 'OpenDataException',
            'NotBoundException', 'DirectoryNotEmptyException', 'CannotProceedException',
            'IllegalFormatPrecisionException', 'AuthenticationNotSupportedException', 'BufferOverflowException',
            'NamingException', 'SQLTransientConnectionException', 'ReferralException', 'InstanceNotFoundException',
            'NotSerializableException', 'MalformedInputException', 'AbstractMethodError', 'LinkLoopException',
            'InvalidApplicationException', 'FileLockInterruptionException', 'UnsupportedFlavorException',
            'ServerNotActiveException', 'ServiceConfigurationError', 'NoClassDefFoundError', 'ConnectException',
            'DOMException', 'IllegalSelectorException', 'XPathExpressionException', 'PolicyError', 'XMLParseException',
            'MissingResourceException', 'ExportException', 'NoSuchFileException', 'SaslException',
            'UnexpectedException', 'SAXException', 'CertificateEncodingException', 'NoSuchMechanismException',
            'ExpandVetoException', 'ProtocolException', 'NotActiveException', 'PropertyException',
            'SyncFactoryException', 'ReadPendingException', 'MalformedObjectNameException',
            'DatatypeConfigurationException', 'FailedLoginException', 'NullPointerException', 'NameNotFoundException',
            'StubNotFoundException', 'ArrayIndexOutOfBoundsException', 'CharConversionException',
            'LimitExceededException', 'CertificateExpiredException', 'InvocationTargetException',
            'IllegalBlockSizeException', 'InvalidRelationTypeException', 'PrinterAbortException', 'OperationsException',
            'SocketSecurityException', 'BootstrapMethodError', 'ExceptionInInitializerError', 'BackingStoreException',
            'BatchUpdateException', 'ServiceNotFoundException', 'CharacterCodingException', 'AccountLockedException',
            'NoninvertibleTransformException', 'SQLFeatureNotSupportedException', 'InvalidParameterSpecException',
            'DirectoryIteratorException', 'CertPathBuilderException', 'IIOException', 'GenericSignatureFormatError',
            'NoSuchAlgorithmException', 'NoSuchMethodException', 'OptionalDataException', 'ActivateFailedException',
            'UnsupportedDataTypeException', 'SQLIntegrityConstraintViolationException', 'SAXParseException',
            'InvalidClassException', 'GSSException', 'DateTimeException', 'JarException', 'URISyntaxException',
            'AttributeModificationException', 'UTFDataFormatException', 'IntrospectionException', 'UnmarshalException',
            'IllegalBlockingModeException', 'NotOwnerException', 'LdapReferralException',
            'UnsupportedLookAndFeelException', 'MissingFormatWidthException', 'SQLNonTransientException',
            'HttpRetryException', 'FilerException', 'MalformedLinkException', 'SkeletonMismatchException',
            'AccessDeniedException', 'RelationServiceNotRegisteredException', 'KeyManagementException',
            'IllegalFormatWidthException', 'LinkageError', 'SSLKeyException', 'PrivilegedActionException',
            'UnsupportedTemporalTypeException', 'SSLProtocolException', 'RelationException', 'XMLSignatureException',
            'SQLSyntaxErrorException', 'PartialResultException', 'UnknownEntityException', 'KeyAlreadyExistsException',
            'ReflectionException', 'UnknownTypeException', 'XPathFactoryConfigurationException',
            'ClosedSelectorException', 'MidiUnavailableException', 'CertificateException',
            'ExemptionMechanismException', 'IllegalArgumentException', 'InterruptedIOException',
            'SAXNotSupportedException', 'AlreadyConnectedException', 'KeyStoreException', 'TransformerException',
            'NoSuchPaddingException', 'LineUnavailableException', 'DataFormatException', 'MalformedParametersException',
            'ServerError', 'NotCompliantMBeanException', 'UnmodifiableSetException', 'InvalidObjectException',
            'SyncProviderException', 'BadStringOperationException', 'ApplicationException',
            'ReflectiveOperationException', 'RelationTypeNotFoundException', 'WritePendingException', 'ServerException',
            'InvalidParameterException', 'AttributeInUseException', 'BadPaddingException', 'XMLStreamException',
            'NegativeArraySizeException', 'BadBinaryOpValueExpException', 'CancelledKeyException',
            'SSLPeerUnverifiedException', 'UnsupportedOperationException', 'CertPathValidatorException',
            'UnknownGroupException', 'UnsupportedEncodingException', 'IllegalPathStateException',
            'UnrecoverableEntryException', 'IllegalMonitorStateException', 'SecurityException',
            'UnknownObjectException', 'AccountExpiredException', 'ActivationException', 'TransactionRequiredException',
            'CertificateRevokedException', 'ClassCastException', 'JMRuntimeException', 'CertificateParsingException',
            'UnsupportedAddressTypeException', 'ZipError', 'PrinterException', 'ClosedDirectoryStreamException',
            'SSLException', 'TransformException', 'InstantiationError', 'AEADBadTagException', 'AlreadyBoundException',
            'SQLNonTransientConnectionException', 'SizeLimitExceededException', 'NoInitialContextException',
            'ZoneRulesException', 'AnnotationTypeMismatchException', 'WriteAbortedException', 'InvalidPathException',
            'SOAPFaultException', 'CloneNotSupportedException', 'NumberFormatException', 'NotContextException',
            'SQLTransientException', 'BrokenBarrierException', 'NoConnectionPendingException',
            'MBeanRegistrationException', 'JAXBException', 'IncompleteAnnotationException', 'MBeanException',
            'PatternSyntaxException', 'ShutdownChannelGroupException', 'LastOwnerException', 'NoSuchMethodError',
            'UnknownServiceException', 'RemarshalException', 'IIOInvalidTreeException',
            'MalformedParameterizedTypeException', 'SystemException', 'PropertyVetoException',
            'InvalidAttributeValueException', 'IllegalFormatFlagsException', 'ProviderException',
            'StreamCorruptedException', 'RoleNotFoundException', 'OutOfMemoryError', 'DigestException', 'EOFException',
            'KeyException', 'ZipException', 'ClassNotFoundException', 'CMMException', 'ServiceUnavailableException',
            'UserPrincipalNotFoundException', 'ReadOnlyBufferException', 'CancellationException', 'XPathException',
            'IllegalAccessException', 'PrintException', 'JMXProviderException', 'RuntimeException',
            'InvalidTransactionException', 'BindException', 'InvalidOpenTypeException', 'CredentialException',
            'DuplicateFormatFlagsException', 'UndeclaredThrowableException', 'ArithmeticException',
            'CertStoreException', 'WebServiceException', 'ConnectionPendingException', 'RuntimeOperationsException',
            'AttributeNotFoundException', 'NoSuchProviderException', 'ConfigurationException',
            'ActivityRequiredException', 'StackOverflowError', 'ScriptException', 'InvalidKeyException',
            'FontFormatException', 'PrinterIOException', 'NoSuchObjectException', 'SchemaViolationException',
            'UnmappableCharacterException', 'InterruptedNamingException', 'UnsupportedCharsetException',
            'AccessException', 'InvalidRelationIdException', 'FileAlreadyExistsException', 'ClassFormatError',
            'UserException', 'LinkException', 'InvalidAttributesException', 'ContextNotEmptyException',
            'IllegalComponentStateException', 'BufferUnderflowException', 'ProviderMismatchException',
            'ConnectIOException', 'SocketTimeoutException', 'CannotUndoException', 'RemoteException',
            'NotYetConnectedException', 'BadAttributeValueExpException', 'DestroyFailedException',
            'RoleInfoNotFoundException', 'SQLTransactionRollbackException', 'URIReferenceException',
            'InvalidRoleInfoException', 'AcceptPendingException', 'CertificateNotYetValidException',
            'FileSystemException', 'NoSuchFieldException', 'EventException', 'TimeLimitExceededException',
            'ClosedChannelException', 'FactoryConfigurationError', 'ShortBufferException',
            'IllegalFormatCodePointException', 'SQLInvalidAuthorizationSpecException', 'SOAPException',
            'TransactionRolledbackException', 'HeadlessException', 'FileNotFoundException', 'CommunicationException',
            'SQLTimeoutException', 'UncheckedIOException', 'UnsupportedAudioFileException',
            'AtomicMoveNotSupportedException', 'StringIndexOutOfBoundsException', 'AWTError',
            'FileSystemAlreadyExistsException', 'NonWritableChannelException', 'ImagingOpException',
            'IndexOutOfBoundsException', 'VirtualMachineError', 'UnknownFormatFlagsException', 'InvalidMarkException',
            'NoSuchElementException', 'FileSystemLoopException', 'RuntimeErrorException', 'TypeNotPresentException',
            'SkeletonNotFoundException', 'MirroredTypesException', 'AnnotationFormatError', 'CompletionException',
            'NoSuchAttributeException', 'RasterFormatException', 'AccountException',
            'InvalidAlgorithmParameterException', 'MirroredTypeException', 'TooManyListenersException',
            'InsufficientResourcesException', 'IOException', 'UnresolvedAddressException', 'ProviderNotFoundException',
            'ServerRuntimeException', 'SQLDataException', 'RMISecurityException', 'DateTimeParseException',
            'InvalidTargetObjectTypeException', 'LSException', 'FormatterClosedException', 'ClosedFileSystemException',
            'UnsupportedCallbackException', 'MarshalException', 'JMXServerErrorException',
            'TransformerFactoryConfigurationError', 'InvalidRoleValueException', 'TransformerConfigurationException',
            'PortUnreachableException', 'ParserConfigurationException', 'InterruptedException', 'IllegalStateException',
            'MissingFormatArgumentException', 'NotYetBoundException', 'ActivityCompletedException',
            'ProfileDataException', 'KeySelectorException', 'InvalidMidiDataException', 'NoPermissionException',
            'CoderMalfunctionError', 'InstanceAlreadyExistsException', 'ChangedCharSetException', 'UnknownError',
            'InvalidPreferencesFormatException', 'IllegalAccessError', 'SQLException',
            'SchemaFactoryConfigurationError', 'UnknownException', 'ExecutionException', 'CredentialNotFoundException',
            'UnknownAnnotationValueException', 'InterruptedByTimeoutException', 'UnknownElementException',
            'RefreshFailedException', 'FileSystemNotFoundException', 'NamingSecurityException',
            'UnrecoverableKeyException', 'CannotRedoException', 'OverlappingFileLockException', 'ParseException',
            'InvalidRelationServiceException', 'XPathFunctionException', 'AssertionError',
            'EnumConstantNotPresentException', 'ClosedWatchServiceException', 'MonitorSettingException',
            'ServerCloneException', 'NoRouteToHostException', 'XAException', 'BadLocationException',
            'IllegalFormatException', 'RejectedExecutionException', 'IllegalChannelGroupException',
            'UnsatisfiedLinkError', 'UnknownUserException', 'InvalidSearchControlsException', 'InstantiationException',
            'InvalidAttributeIdentifierException', 'RelationNotFoundException', 'MalformedURLException',
            'UnknownFormatConversionException', 'NoSuchFieldError', 'AccountNotFoundException',
            'OperationNotSupportedException', 'AWTException', 'UnmodifiableClassException',
            'InvalidDnDOperationException', 'AccessControlException', 'NotDirectoryException', 'SerialException',
            'ConcurrentModificationException', 'GeneralSecurityException', 'MimeTypeParseException',
            'InvalidActivityException', 'InputMismatchException', 'IOError', 'FormatFlagsConversionMismatchException',
            'NotLinkException', 'IllegalCharsetNameException', 'DataBindingException', 'Exception', 'Error'
            ]
java_nonstd = ['MojoFailureException', 'MojoExecutionException', 'BuildException', 'NotImplementedException',
               'ProjectBuildingException', 'LifecycleExecutionException', 'TaskExecutionException', 'GradleException',
               'AssertionFailedError', 'ReportedException', 'DependencyResolutionException',
               'UnresolvableModelException', 'CompilationFailureException', 'MavenRuntimeException',
               'PluginResolutionException', 'SQLRuntimeException', 'GradleScriptException', 'MavenInvocationException',
               'MavenReportException', 'ProjectConfigurationException'
               ]
python_exceptions = ['BaseException', 'SystemExit', 'OverflowError', 'KeyboardInterrupt', 'UserWarning', 'OSError',
                     'TabError', 'FileExistsError', 'FutureWarning', 'PendingDeprecationWarning', 'SystemError',
                     'EOFError', 'ZeroDivisionError', 'NotImplementedError', 'GeneratorExit', 'UnicodeError',
                     'RuntimeWarning', 'BrokenPipeError', 'MemoryError', 'StandardError', 'BytesWarning',
                     'RecursionError', 'ConnectionResetError', 'IndexError', 'AssertionError', 'TimeoutError',
                     'ImportError', 'EnvironmentError', 'ReferenceError', 'UnicodeTranslateError', 'StopIteration',
                     'WindowsError (Windows)', 'KeyError', 'DeprecationWarning', 'UnboundLocalError', 'PermissionError',
                     'SyntaxError', 'UnicodeDecodeError', 'LookupError', 'FloatingPointError', 'IsADirectoryError',
                     'AttributeError', 'ValueError', 'UnicodeWarning', 'ConnectionRefusedError', 'NameError',
                     'ConnectionError', 'ArithmeticError', 'ConnectionAbortedError', 'StopAsyncIteration', 'IOError',
                     'TypeError', 'RuntimeError', 'IndentationError', 'ModuleNotFoundError', 'ImportWarning',
                     'BlockingIOError', 'FileNotFoundError', 'ProcessLookupError', 'InterruptedError', 'Warning',
                     'ResourceWarning', 'BufferError', 'ChildProcessError', 'VMSError (VMS)', 'SyntaxWarning',
                     'NotADirectoryError', 'UnicodeEncodeError', 'Exception'
                     ]
python_nonstd = ['InvocationError', 'PessimisticLockingFailureException',
                 'JSONDecodeError', 'PicklingError', 'ResourceNotFoundException', 'DataAccessException']
not_errors = ['throwError', 'throwException']
