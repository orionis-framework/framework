from abc import ABC, abstractmethod

class IReflectionModule(ABC):

    @abstractmethod
    def getModule(self) -> object:
        """
        Return the imported module object.

        Returns
        -------
        object
            The imported module object.
        """

    @abstractmethod
    def hasClass(self, class_name: str) -> bool:
        """
        Check if a class with the specified name exists in the module.

        Parameters
        ----------
        class_name : str
            Name of the class to check.

        Returns
        -------
        bool
            True if the class exists in the module, otherwise False.
        """

    @abstractmethod
    def getClass(self, class_name: str) -> type | None:
        """
        Retrieve a class object by its name from the module.

        Parameters
        ----------
        class_name : str
            Name of the class to retrieve.

        Returns
        -------
        type or None
            The class object if found, otherwise None.
        """

    @abstractmethod
    def setClass(self, class_name: str, cls: type) -> bool:
        """
        Set a class in the module.

        Parameters
        ----------
        class_name : str
            Name of the class to set.
        cls : type
            Class object to set.

        Raises
        ------
        ValueError
            If `cls` is not a class type, if `class_name` is not a valid identifier,
            or if `class_name` is a reserved keyword.

        Returns
        -------
        bool
            True if the class was set successfully.
        """

    @abstractmethod
    def removeClass(self, class_name: str) -> bool:
        """
        Remove a class from the module.

        Parameters
        ----------
        class_name : str
            Name of the class to remove.

        Raises
        ------
        ValueError
            If `class_name` is not a valid identifier or if the class does not exist.

        Returns
        -------
        bool
            True if the class was removed successfully.
        """

    @abstractmethod
    def getClasses(self) -> dict:
        """
        Return a dictionary of classes defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with class names as keys and class objects as values.
        """

    @abstractmethod
    def getPublicClasses(self) -> dict:
        """
        Return a dictionary of public classes defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with class names as keys and class objects as values.
        """

    @abstractmethod
    def getProtectedClasses(self) -> dict:
        """
        Return a dictionary of protected classes defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with class names as keys and class objects as values.
        """

    @abstractmethod
    def getPrivateClasses(self) -> dict:
        """
        Return a dictionary of private classes defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with class names as keys and class objects as values.
        """

    @abstractmethod
    def getConstant(self, constant_name: str) -> object | None:
        """
        Retrieve a constant value by name from the module.

        Parameters
        ----------
        constant_name : str
            Name of the constant to retrieve.

        Returns
        -------
        object or None
            Value of the constant if found, otherwise None.
        """

    @abstractmethod
    def getConstants(self) -> dict:
        """
        Retrieve constants defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with constant names as keys and their values as values.
        """

    @abstractmethod
    def getPublicConstants(self) -> dict:
        """
        Retrieve public constants defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with constant names as keys and their values as values.
        """

    @abstractmethod
    def getProtectedConstants(self) -> dict:
        """
        Return protected constants defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with constant names as keys and their values as values.
        """

    @abstractmethod
    def getPrivateConstants(self) -> dict:
        """
        Retrieve private constants defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with constant names as keys and their values as values.
        """

    @abstractmethod
    def getFunctions(self) -> dict:
        """
        Return a dictionary of functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with function names as keys and function objects as values.
        """

    @abstractmethod
    def getPublicFunctions(self) -> dict:
        """
        Return a dictionary of public functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """

    @abstractmethod
    def getPublicSyncFunctions(self) -> dict:
        """
        Return a dictionary of public synchronous functions in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """

    @abstractmethod
    def getPublicAsyncFunctions(self) -> dict:
        """
        Return a dictionary of public asynchronous functions in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """

    @abstractmethod
    def getProtectedFunctions(self) -> dict:
        """
        Return a dictionary of protected functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping protected function names to function objects.
        """

    @abstractmethod
    def getProtectedSyncFunctions(self) -> dict:
        """
        Return protected synchronous functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """

    @abstractmethod
    def getProtectedAsyncFunctions(self) -> dict:
        """
        Return protected asynchronous functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """

    @abstractmethod
    def getPrivateFunctions(self) -> dict:
        """
        Return private functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """

    @abstractmethod
    def getPrivateSyncFunctions(self) -> dict:
        """
        Return private synchronous functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with function names as keys and function objects as values.
        """

    @abstractmethod
    def getPrivateAsyncFunctions(self) -> dict:
        """
        Return private asynchronous functions defined in the module.

        Returns
        -------
        dict
            Dictionary with function names as keys and function objects as values.
        """

    @abstractmethod
    def getImports(self) -> dict:
        """
        Retrieve imported modules from the module.

        Returns
        -------
        dict
            Dictionary mapping import names to module objects.
        """

    @abstractmethod
    def getFile(self) -> str:
        """
        Return the file path of the module.

        Returns
        -------
        str
            The absolute file path of the module.
        """

    @abstractmethod
    def getSourceCode(self) -> str:
        """
        Retrieve the source code of the module.

        Returns
        -------
        str
            The source code of the module as a string.

        Raises
        ------
        ValueError
            If the source code cannot be read from the module file.
        """

    @abstractmethod
    def clearCache(self) -> None:
        """
        Clear all cached reflection data.

        Removes all cached entries stored in the reflection instance. Forces
        fresh computation on subsequent method calls.

        Parameters
        ----------
        None

        Returns
        -------
        None
            This method does not return a value.
        """
