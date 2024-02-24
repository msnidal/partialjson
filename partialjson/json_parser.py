from calendar import c
import json


class JSONParser:
    def __init__(self):
        self.parsers = {
            " ": self.parse_space,
            "\r": self.parse_space,
            "\n": self.parse_space,
            "\t": self.parse_space,
            "[": self.parse_array,
            "{": self.parse_object,
            '"': self.parse_string,
            "t": self.parse_true,
            "f": self.parse_false,
            "n": self.parse_null,
        }
        # Adding parsers for numbers
        for c in "0123456789.-":
            self.parsers[c] = self.parse_number

        self.last_parse_reminding = None
        self.on_extra_token = self.default_on_extra_token

    def default_on_extra_token(self, text, data, reminding):
        print(
            "Parsed JSON with extra tokens:",
            {"text": text, "data": data, "reminding": reminding},
        )

    def parse(self, s) -> tuple[dict | list, list[str]]:
        """Parse a JSON string and return the parsed data and the keys that are complete in the data.
        Args:
            s (str): The JSON string to parse.
        Returns:
            tuple[dict | list, list[str]]: The parsed data and the keys that are complete in the data.
        """
        if len(s) >= 1:
            try:
                result = json.loads(s)
                if isinstance(result, dict):
                    complete_keys = list(result.keys())
                else:
                    complete_keys = []

                return result, complete_keys
            except json.JSONDecodeError as e:
                data, reminding, _ = self.parse_any(s, e)

                self.last_parse_reminding = reminding
                if self.on_extra_token and reminding:
                    self.on_extra_token(s, data, reminding)

                result = json.loads(json.dumps(data))
                if isinstance(result, dict):
                    complete_keys = list(result.keys())
                    if len(complete_keys) == 0:
                        complete_keys = []
                    else:
                        complete_keys = complete_keys[:-1]
                else:
                    complete_keys = []

                return result, complete_keys
        else:
            return json.loads("{}"), []

    def parse_any(self, s, e) -> tuple[dict | list, str, bool]:
        """Parse any JSON value from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[dict | list, str, bool]: The parsed value, the remaining string, and a flag indicating if the value is complete.
        """
        if not s:
            raise e
        parser = self.parsers.get(s[0])
        if not parser:
            raise e
        return parser(s, e)

    def parse_space(self, s, e) -> tuple[dict | list, str, bool]:
        """Parse a space from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[dict | list, str, bool]: The parsed space, the remaining string, and a flag indicating if the space is complete.
        """
        return self.parse_any(s.strip(), e)

    def parse_array(self, s, e) -> tuple[list, str, bool]:
        """Parse an array from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[list, str, bool]: The parsed array, the remaining string, and a flag indicating if the array is complete.
        """
        s = s[1:]  # skip starting '['
        acc = []
        s = s.strip()

        has_any_incomplete = False
        while s:
            if s[0] == "]":
                s = s[1:]  # skip ending ']'
                break
            res, s, is_complete = self.parse_any(s, e)
            if not is_complete:
                has_any_incomplete = True

            acc.append(res)
            s = s.strip()
            if s.startswith(","):
                s = s[1:]
                s = s.strip()
        return acc, s, not has_any_incomplete

    def parse_object(self, s, e) -> tuple[dict, str, bool]:
        """Parse an object from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[dict, str, bool]: The parsed object, the remaining string, and a flag indicating if the object is complete.
        """
        s = s[1:]  # skip starting '{'
        acc = {}
        s = s.strip()

        has_any_incomplete = False
        while s:
            if s[0] == "}":
                s = s[1:]  # skip ending '}'
                break
            key, s, is_complete = self.parse_any(s, e)
            if not is_complete:
                has_any_incomplete = True

            s = s.strip()

            # Handle case where object ends after a key
            if not s or s[0] == "}":
                acc[key] = None
                has_any_incomplete = True
                break

            # Expecting a colon after the key
            if s[0] != ":":
                has_any_incomplete = True
                raise e  # or handle this scenario as per your requirement

            s = s[1:]  # skip ':'
            s = s.strip()

            # Handle case where value is missing or incomplete
            if not s or s[0] in ",}":
                acc[key] = None
                if s.startswith(","):
                    s = s[1:]

                has_any_incomplete = True
                break

            value, s, is_complete = self.parse_any(s, e)
            if not is_complete:
                has_any_incomplete = True

            acc[key] = value
            s = s.strip()
            if s.startswith(","):
                s = s[1:]
                s = s.strip()

        return acc, s, not has_any_incomplete

    def parse_string(self, s, e) -> tuple[str, str, bool]:
        """Parse a string from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[str, str, bool]: The parsed string, the remaining string, and a flag indicating if the string is complete.
        """
        end = s.find('"', 1)
        while end != -1 and s[end - 1] == "\\":  # Handle escaped quotes
            end = s.find('"', end + 1)
        if end == -1:
            return (
                s[1:],
                "",
                False,
            )  # Return the incomplete string without the opening quote
        str_val = s[: end + 1]
        s = s[end + 1 :]
        return json.loads(str_val), s, True

    def parse_number(self, s, e) -> tuple[float | int, str, bool]:
        """Parse a number from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[float | int, str]: The parsed number and the remaining string.
        """
        i = 0
        while i < len(s) and s[i] in "0123456789.-":
            i += 1
        num_str = s[:i]
        s = s[i:]
        if not num_str or num_str.endswith(".") or num_str.endswith("-"):
            return num_str, "", False  # Return the incomplete number as is
        try:
            num = (
                float(num_str)
                if "." in num_str or "e" in num_str or "E" in num_str
                else int(num_str)
            )
        except ValueError:
            raise e
        return num, s, True

    def parse_true(self, s, e) -> tuple[bool, str, bool]:
        """Parse a true value from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[bool, str, bool]: The parsed true value, the remaining string, and a flag indicating if the true value is complete.
        """
        if s.startswith("true"):
            return True, s[4:], True
        raise e

    def parse_false(self, s, e) -> tuple[bool, str, bool]:
        """Parse a false value from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[bool, str, bool]: The parsed false value, the remaining string, and a flag indicating if the false value is complete.
        """
        if s.startswith("false"):
            return False, s[5:], True
        raise e

    def parse_null(self, s, e) -> tuple[None, str, bool]:
        """Parse a null value from the given string.
        Args:
            s (str): The string to parse.
            e (json.JSONDecodeError): The exception to raise if the string is invalid.
        Returns:
            tuple[None, str, bool]: The parsed null value, the remaining string, and a flag indicating if the null value is complete.
        """
        if s.startswith("null"):
            return None, s[4:], True
        raise e
